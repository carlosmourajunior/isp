from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend
from django_rq import get_queue
from django.db.models import Q, Count, Avg, Max, Min
from .models import (
    ONU, OltUsers, PlacaOnu, ClienteFibraIxc,
    OltSystemInfo, OltSlot, OltTemperature, OltSfpDiagnostics
)
from .serializers import (
    ONUSerializer,
    ONUDetailSerializer,
    OltUsersSerializer,
    PlacaOnuSerializer,
    ClienteFibraIxcSerializer,
    ClienteFibraIxcInternalSerializer,
    OltSystemInfoSerializer,
    OltSlotSerializer,
    OltTemperatureSerializer,
    OltSfpDiagnosticsSerializer,
    OltSystemStatsSerializer
)
from .utils import OltSystemCollector, olt_connector
from .security import frontend_only, olt_admin_required
from .scheduler import get_scheduler_status
from .tasks import (
    update_port_occupation_task,
    update_onus_task,
    update_mac_task,
    update_clientes_task,
    comprehensive_update_task,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token view para adicionar informações extras no token
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = request.user if hasattr(request, 'user') else None
            response.data['user_info'] = {
                'username': request.data.get('username'),
                'message': 'Login realizado com sucesso'
            }
        return response


class ONUListAPIView(generics.ListAPIView):
    """
    Lista todas as ONUs com filtros e paginação
    """
    queryset = ONU.objects.all().order_by('pon', 'position')
    serializer_class = ONUSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['oper_state', 'admin_state', 'cliente_fibra', 'pon']
    search_fields = ['serial', 'mac', 'desc1', 'desc2', 'pon']
    ordering_fields = ['position', 'olt_rx_sig', 'pon']


class ONUDetailAPIView(generics.RetrieveAPIView):
    """
    Detalhes de uma ONU específica com informações do cliente
    """
    queryset = ONU.objects.all()
    serializer_class = ONUDetailSerializer
    permission_classes = [IsAuthenticated]


class OltUsersListAPIView(generics.ListAPIView):
    """
    Lista informações das portas OLT
    """
    queryset = OltUsers.objects.all().order_by('slot', 'port')
    serializer_class = OltUsersSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['slot']
    ordering_fields = ['slot', 'port', 'users_connected', 'last_updated']


class ClienteFibraListAPIView(generics.ListAPIView):
    """
    Lista clientes fibra
    """
    queryset = ClienteFibraIxc.objects.all()
    serializer_class = ClienteFibraIxcSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['nome', 'mac', 'endereco']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def onu_stats(request):
    """
    Estatísticas gerais das ONUs
    """
    total_onus = ONU.objects.count()
    onus_online = ONU.objects.filter(oper_state='up').count()
    onus_offline = ONU.objects.filter(oper_state='down').count()
    clientes_fibra = ONU.objects.filter(cliente_fibra=True).count()
    
    # Estatísticas por slot
    slot_stats = {}
    for slot in [1, 2]:
        slot_onus = ONU.objects.filter(pon__contains=f'/1/{slot}/')
        slot_stats[f'slot_{slot}'] = {
            'total': slot_onus.count(),
            'online': slot_onus.filter(oper_state='up').count(),
            'offline': slot_onus.filter(oper_state='down').count()
        }
    
    # ONUs com sinal baixo (menor que -25 dBm)
    low_signal = ONU.objects.filter(olt_rx_sig__lt=-25.0).count()
    
    return Response({
        'total_onus': total_onus,
        'onus_online': onus_online,
        'onus_offline': onus_offline,
        'clientes_fibra': clientes_fibra,
        'onus_sinal_baixo': low_signal,
        'estatisticas_por_slot': slot_stats,
        'percentual_online': round((onus_online / total_onus * 100), 2) if total_onus > 0 else 0
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def onu_by_pon(request, pon):
    """
    Lista ONUs de uma PON específica
    """
    onus = ONU.objects.filter(pon=pon).order_by('position')
    if not onus.exists():
        return Response(
            {'error': f'Nenhuma ONU encontrada na PON {pon}'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = ONUSerializer(onus, many=True)
    return Response({
        'pon': pon,
        'total_onus': onus.count(),
        'onus': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def onu_search(request):
    """
    Busca avançada de ONUs
    """
    query = request.GET.get('q', '')
    if not query:
        return Response({'error': 'Parâmetro de busca "q" é obrigatório'}, status=400)
    
    # Busca por serial, MAC, descrição ou PON
    onus = ONU.objects.filter(
        Q(serial__icontains=query) |
        Q(mac__icontains=query) |
        Q(desc1__icontains=query) |
        Q(desc2__icontains=query) |
        Q(pon__icontains=query)
    ).order_by('pon', 'position')
    
    serializer = ONUDetailSerializer(onus, many=True)
    return Response({
        'query': query,
        'total_resultados': onus.count(),
        'resultados': serializer.data
    })


# =========== OLT SYSTEM API VIEWS ===========

class OltSystemInfoAPIView(generics.RetrieveAPIView):
    """
    Informações do sistema OLT
    """
    queryset = OltSystemInfo.objects.all()
    serializer_class = OltSystemInfoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        # Retorna o primeiro (e único) registro de sistema
        obj, created = OltSystemInfo.objects.get_or_create(id=1)
        return obj


class OltSlotListAPIView(generics.ListAPIView):
    """
    Lista slots da OLT
    """
    queryset = OltSlot.objects.all().order_by('slot_name')
    serializer_class = OltSlotSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['enabled', 'availability', 'actual_type']
    ordering_fields = ['slot_name', 'actual_type', 'restart_count']


class OltTemperatureListAPIView(generics.ListAPIView):
    """
    Lista temperaturas da OLT
    """
    queryset = OltTemperature.objects.all().order_by('slot_name', 'sensor_id')
    serializer_class = OltTemperatureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['slot_name']
    ordering_fields = ['slot_name', 'sensor_id', 'actual_temp']


class OltSfpDiagnosticsListAPIView(generics.ListAPIView):
    """
    Lista diagnósticos SFP da OLT
    """
    queryset = OltSfpDiagnostics.objects.all().order_by('interface')
    serializer_class = OltSfpDiagnosticsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['interface', 'temperature', 'tx_power', 'rx_power']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def olt_system_stats(request):
    """
    Estatísticas completas do sistema OLT
    """
    try:
        # Informações do sistema
        system_info = OltSystemInfo.objects.first()
        
        # Estatísticas dos slots
        total_slots = OltSlot.objects.count()
        operational_slots = OltSlot.objects.filter(
            enabled=True, 
            availability='available', 
            error_status='no-error'
        ).count()
        offline_slots = total_slots - operational_slots
        
        slots_by_type = OltSlot.objects.values('actual_type').annotate(
            count=Count('id')
        ).order_by('actual_type')
        
        # Estatísticas de temperatura
        temps = OltTemperature.objects.all()
        critical_temps = temps.filter(actual_temp__gte=75).count()  # Temperatura crítica
        warning_temps = temps.filter(actual_temp__gte=70, actual_temp__lt=75).count()
        
        temp_stats = temps.aggregate(
            avg_temp=Avg('actual_temp'),
            max_temp=Max('actual_temp'),
            min_temp=Min('actual_temp')
        )
        
        # Temperaturas por slot
        temp_by_slot = temps.values('slot_name').annotate(
            avg_temp=Avg('actual_temp'),
            max_temp=Max('actual_temp'),
            sensor_count=Count('id')
        ).order_by('slot_name')
        
        response_data = {
            'system_info': OltSystemInfoSerializer(system_info).data if system_info else None,
            'slots_stats': {
                'total_slots': total_slots,
                'operational_slots': operational_slots,
                'offline_slots': offline_slots,
                'slots_by_type': list(slots_by_type),
                'operational_percentage': round((operational_slots / total_slots * 100), 2) if total_slots > 0 else 0
            },
            'temperature_stats': {
                'critical_temperatures': critical_temps,
                'warning_temperatures': warning_temps,
                'normal_temperatures': temps.count() - critical_temps - warning_temps,
                'average_temperature': round(temp_stats['avg_temp'], 1) if temp_stats['avg_temp'] else 0,
                'max_temperature': temp_stats['max_temp'] or 0,
                'min_temperature': temp_stats['min_temp'] or 0,
                'temperature_by_slot': list(temp_by_slot)
            },
            'last_updated': system_info.last_updated if system_info else None
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao obter estatísticas: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@frontend_only
@olt_admin_required
def update_olt_system_data(request):
    """
    Atualiza dados do sistema OLT coletando da OLT
    ⚠️ ACESSO RESTRITO: Apenas via frontend interno e usuários admin
    """
    try:
        collector = OltSystemCollector()
        result = collector.collect_all_system_data()
        
        if result:
            return Response({
                'message': 'Dados do sistema OLT atualizados com sucesso',
                'system_info': OltSystemInfoSerializer(result['system_info']).data if result['system_info'] else None,
                'slots_count': result['slots'].count() if result['slots'] else 0,
                'temperatures_count': result['temperatures'].count() if result['temperatures'] else 0,
                'security_info': {
                    'access_type': 'frontend_internal',
                    'user': request.user.username,
                    'timestamp': result.get('timestamp', 'N/A')
                }
            })
        else:
            return Response(
                {'error': 'Falha ao coletar dados da OLT'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        return Response(
            {'error': f'Erro ao atualizar dados: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def olt_temperature_alerts(request):
    """
    Lista temperaturas em estado de alerta
    """
    try:
        # Temperaturas críticas e de aviso
        critical_temps = OltTemperature.objects.filter(actual_temp__gte=75)
        warning_temps = OltTemperature.objects.filter(actual_temp__gte=70, actual_temp__lt=75)
        
        response_data = {
            'critical_alerts': OltTemperatureSerializer(critical_temps, many=True).data,
            'warning_alerts': OltTemperatureSerializer(warning_temps, many=True).data,
            'critical_count': critical_temps.count(),
            'warning_count': warning_temps.count()
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao consultar alertas de temperatura: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== ENDPOINTS DE INFORMAÇÃO (SOMENTE LEITURA) ====================
# Estes endpoints NÃO acessam a OLT diretamente, apenas consultam dados já coletados

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def olt_connection_status(request):
    """
    Verifica status da conexão com a OLT (sem conectar)
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        
        # Verificar última atualização dos dados
        latest_system_info = OltSystemInfo.objects.order_by('-last_updated').first()
        
        if latest_system_info:
            time_diff = timezone.now() - latest_system_info.last_updated
            is_recent = time_diff < timedelta(minutes=30)
            
            return Response({
                'connection_status': 'online' if is_recent else 'outdated',
                'last_update': latest_system_info.last_updated,
                'minutes_ago': int(time_diff.total_seconds() / 60),
                'system_uptime': latest_system_info.uptime_raw,
                'note': 'Dados baseados na última coleta, não em conexão em tempo real'
            })
        else:
            return Response({
                'connection_status': 'unknown',
                'message': 'Nenhum dado do sistema encontrado',
                'note': 'Execute uma atualização via frontend para coletar dados'
            })
            
    except Exception as e:
        return Response(
            {'error': f'Erro ao verificar status: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ==================== ENDPOINTS DO FRONTEND INTERNO (React) ====================
# Portam ações que hoje só existem como views de template em olt/views.py.
# NÃO fazem parte do contrato congelado de parceiros (API_DOCUMENTATION.md) -
# essa distinção é só de uso/documentação, tecnicamente vivem no mesmo /api/.

def _job_info(job, include_error=False):
    info = {
        'id': job.id,
        'func_name': job.func_name,
        'status': job.get_status(),
        'created_at': job.created_at,
        'user': job.meta.get('user', 'N/A'),
        'menu_item': job.meta.get('menu_item', 'N/A'),
        'started_at': job.meta.get('started_at', 'N/A'),
        'current_step': job.meta.get('current_step', 'N/A'),
    }
    if include_error:
        info['error_message'] = job.exc_info
    return info


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_list(request):
    """
    Status das tarefas em background (RQ). Substitui a página tasks.html,
    que hoje só se atualiza via full-page reload a cada 5s.
    """
    queue = get_queue('default')

    running_jobs = []
    for job_id in queue.started_job_registry.get_job_ids()[:5]:
        job = queue.fetch_job(job_id)
        if job is not None:
            running_jobs.append(_job_info(job))

    queued_jobs = []
    for job in list(queue.jobs)[:5]:
        if job is not None and job.get_status() in ['queued', 'deferred']:
            queued_jobs.append(_job_info(job))

    failed_jobs = []
    for job_id in queue.failed_job_registry.get_job_ids()[:5]:
        job = queue.fetch_job(job_id)
        if job is not None:
            failed_jobs.append(_job_info(job, include_error=True))

    finished_jobs = []
    for job_id in queue.finished_job_registry.get_job_ids()[:5]:
        job = queue.fetch_job(job_id)
        if job is not None:
            finished_jobs.append(_job_info(job))

    return Response({
        'running_jobs': running_jobs,
        'queued_jobs': queued_jobs,
        'finished_jobs': finished_jobs,
        'failed_jobs': failed_jobs,
    })


def _enqueue_task(request, task_func, menu_item):
    job = task_func.delay(user=request.user.username, menu_item=menu_item)
    return Response({'job_id': job.id, 'menu_item': menu_item}, status=status.HTTP_202_ACCEPTED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_update_ports(request):
    """Dispara a atualização de ocupação das portas OLT"""
    return _enqueue_task(request, update_port_occupation_task, 'Atualização de Portas')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_update_onus(request):
    """Dispara a atualização das ONUs"""
    return _enqueue_task(request, update_onus_task, 'Atualização de ONUs')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_update_mac(request):
    """Dispara a atualização dos endereços MAC"""
    return _enqueue_task(request, update_mac_task, 'Atualização de MAC')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_sync_clientes(request):
    """Dispara a sincronização de clientes fibra (IXC)"""
    return _enqueue_task(request, update_clientes_task, 'Atualização de Clientes Fibra')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_update_all(request):
    """Dispara a sequência completa de atualizações, incluindo dados da OLT"""
    return _enqueue_task(request, comprehensive_update_task, 'Atualizar Todos os Dados Completo')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def scheduler_status_api(request):
    """Status do scheduler de atualizações automáticas"""
    try:
        scheduler_data = get_scheduler_status()
        queue = get_queue('default')
        return Response({
            'scheduler': scheduler_data,
            'queue': {
                'pending_jobs': len(queue),
                'failed_jobs': len(queue.failed_job_registry),
                'finished_jobs': len(queue.finished_job_registry),
            },
        })
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@frontend_only
@olt_admin_required
def remove_onu_view(request, slot, port, position):
    """
    Remove uma ONU: comando na OLT real + remoção do registro no banco.
    Consolida o que hoje são duas views de template (remover_ont, que tem
    um bug de path e não apaga do banco, e delete, que é a versão completa
    e efetivamente usada pela UI) num único endpoint.
    """
    pon = f"1/1/{slot}/{port}/{position}"
    connector = olt_connector()
    try:
        connector.remove_onu(pon)
    except Exception as e:
        return Response(
            {'error': f'Erro ao remover ONU {pon}: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    deleted_count, _ = ONU.objects.filter(pon=f"1/1/{slot}/{port}", position=position).delete()
    return Response({'message': f'ONU {pon} removida', 'deleted_from_db': deleted_count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@frontend_only
@olt_admin_required
def reset_onu_view(request, slot, port, position):
    """Reinicia uma ONU na OLT"""
    pon = f"1/1/{slot}/{port}/{position}"
    connector = olt_connector()
    try:
        connector.reset_onu(pon)
    except Exception as e:
        return Response(
            {'error': f'Erro ao reiniciar ONU {pon}: {e}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response({'message': f'ONU {pon} reiniciada com sucesso'})


class DuplicatedOnuListAPIView(generics.ListAPIView):
    """ONUs com número serial duplicado"""
    serializer_class = ONUSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        duplicated_serials = (
            ONU.objects.values('serial')
            .annotate(total=Count('id'))
            .filter(total__gt=1)
            .values_list('serial', flat=True)
        )
        return ONU.objects.filter(serial__in=duplicated_serials).order_by('serial', 'pon')


class MacAddressListAPIView(generics.ListAPIView):
    """Lista de ONUs para consulta de endereços MAC, com busca"""
    queryset = ONU.objects.all().order_by('mac')
    serializer_class = ONUSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['mac', 'serial', 'desc1', 'desc2']


class OnuWithoutMacListAPIView(generics.ListAPIView):
    """ONUs sem MAC cadastrado (mac vazio ou nulo)"""
    serializer_class = ONUSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['serial', 'desc1', 'desc2', 'pon']

    def get_queryset(self):
        return ONU.objects.filter(Q(mac__isnull=True) | Q(mac='')).order_by('pon', 'position')


class ClienteFibraInternalListAPIView(generics.ListAPIView):
    """
    Clientes Fibra pro frontend interno - inclui 'vinculado' (existe contrato
    real no IXC por trás do registro, ver ClienteFibraIxc.vinculado) e
    permite filtrar por ele. Não é o contrato congelado de parceiros
    (esse continua em ClienteFibraListAPIView/ClienteFibraIxcSerializer).
    """
    queryset = ClienteFibraIxc.objects.all().order_by('nome')
    serializer_class = ClienteFibraIxcInternalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['vinculado']
    search_fields = ['nome', 'mac', 'endereco']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def onu_health_summary(request):
    """
    Contagens usadas nos cards do dashboard (equivalente ao que a view
    `home` de template calculava linha a linha): ONUs sem MAC, sem cliente
    fibra associado, e faixas de sinal baixo.
    """
    onus_sem_mac = ONU.objects.filter(Q(mac__isnull=True) | Q(mac='')).count()
    onus_sem_cliente = ONU.objects.filter(cliente_fibra=False).count()
    sinal_abaixo_29 = ONU.objects.filter(olt_rx_sig__lt=-29).count()
    sinal_entre_27_e_29 = ONU.objects.filter(olt_rx_sig__gte=-29, olt_rx_sig__lte=-27).count()

    return Response({
        'onus_sem_mac': onus_sem_mac,
        'onus_sem_cliente_fibra': onus_sem_cliente,
        'sinal_abaixo_29': sinal_abaixo_29,
        'sinal_entre_27_e_29': sinal_entre_27_e_29,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ftth_boxes_by_occupancy(request):
    """Caixas FTTH ordenadas por quantidade de clientes"""
    search = request.GET.get('search', '')
    queryset = ClienteFibraIxc.objects.values('id_caixa_ftth').annotate(
        client_count=Count('id_caixa_ftth')
    ).order_by('-client_count')

    if search:
        queryset = queryset.filter(id_caixa_ftth__icontains=search)

    paginator = PageNumberPagination()
    paginator.page_size = 50
    page = paginator.paginate_queryset(list(queryset), request)
    return paginator.get_paginated_response(page)