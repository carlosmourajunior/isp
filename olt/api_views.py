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
    ONU, Olt, OltUsers, PlacaOnu, ClienteFibraIxc,
    OltSystemInfo, OltSlot, OltTemperature, OltSfpDiagnostics
)
from .serializers import (
    ONUSerializer,
    ONUDetailSerializer,
    OltSerializer,
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


# Campos ordenáveis compartilhados por toda view baseada em ONU/ONUSerializer
# (lista principal + duplicadas/MAC/sem-MAC) - mantém as 4 sincronizadas, já
# que representam o mesmo conjunto de colunas exibidas no frontend.
ONU_ORDERING_FIELDS = [
    'pon', 'position', 'mac', 'serial', 'oper_state', 'admin_state',
    'olt_rx_sig', 'ont_rx_sig', 'ont_tx_sig', 'desc1', 'desc2', 'cliente_fibra', 'olt__name',
]


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
    filterset_fields = {
        'oper_state': ['exact'],
        'admin_state': ['exact'],
        'cliente_fibra': ['exact'],
        'pon': ['exact'],
        'olt': ['exact'],
        # gte/lte/lt pra permitir as telas de "sinal baixo"/"sinal crítico" do dashboard
        'olt_rx_sig': ['exact', 'gte', 'lte', 'lt', 'gt'],
        'ont_rx_sig': ['exact', 'gte', 'lte', 'lt', 'gt'],
    }
    search_fields = ['serial', 'mac', 'desc1', 'desc2', 'pon']
    ordering_fields = ONU_ORDERING_FIELDS


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
    filterset_fields = ['slot', 'olt']
    ordering_fields = ['slot', 'port', 'users_connected', 'last_updated', 'olt__name']


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
    
    # Estatísticas por slot - descobre os slots realmente usados a partir dos
    # PONs distintos em vez de supor um número fixo (OLTs diferentes têm
    # capacidades diferentes, ver Olt.slot_count).
    slots_presentes = set()
    for pon in ONU.objects.values_list('pon', flat=True).distinct():
        partes = pon.split('/')
        if len(partes) >= 3 and partes[2].isdigit():
            slots_presentes.add(int(partes[2]))

    slot_stats = {}
    for slot in sorted(slots_presentes):
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


# =========== CADASTRO DE OLTs (multi-OLT) ===========
# CRUD restrito a admins - guarda credencial de acesso real ao equipamento.

class OltListCreateAPIView(generics.ListCreateAPIView):
    """Lista e cadastra OLTs"""
    queryset = Olt.objects.all()
    serializer_class = OltSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_active', 'vendor']
    ordering_fields = ['name', 'vendor', 'host', 'slot_count', 'is_active', 'created_at']

    def get_permissions(self):
        # Leitura: qualquer usuário autenticado (pra popular filtros de OLT
        # nas telas). Cadastro: só admin (olt_admin_required abaixo faz a
        # checagem real de escrita).
        return [IsAuthenticated()]

    def post(self, request, *args, **kwargs):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'Apenas administradores podem cadastrar OLTs', 'code': 'ADMIN_REQUIRED'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().post(request, *args, **kwargs)


class OltDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Detalhe, edição e remoção de uma OLT"""
    queryset = Olt.objects.all()
    serializer_class = OltSerializer
    permission_classes = [IsAuthenticated]

    def check_write_permission(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'Apenas administradores podem alterar OLTs', 'code': 'ADMIN_REQUIRED'},
                status=status.HTTP_403_FORBIDDEN
            )
        return None

    def put(self, request, *args, **kwargs):
        denied = self.check_write_permission(request)
        return denied or super().put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        denied = self.check_write_permission(request)
        return denied or super().patch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        denied = self.check_write_permission(request)
        return denied or super().delete(request, *args, **kwargs)


# =========== OLT SYSTEM API VIEWS ===========

class OltSystemInfoAPIView(generics.RetrieveAPIView):
    """
    Informações do sistema OLT
    """
    queryset = OltSystemInfo.objects.all()
    serializer_class = OltSystemInfoSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Com múltiplas OLTs, retorna o registro da OLT padrão (primeira
        # ativa) - mantém o contrato de antes pra quem consome esse
        # endpoint sem escolher uma OLT explicitamente.
        from .utils import get_default_olt
        from django.http import Http404
        olt = get_default_olt()
        if olt is None:
            raise Http404('Nenhuma OLT ativa cadastrada')
        obj, created = OltSystemInfo.objects.get_or_create(olt=olt)
        return obj


class OltSlotListAPIView(generics.ListAPIView):
    """
    Lista slots da OLT
    """
    queryset = OltSlot.objects.all().order_by('slot_name')
    serializer_class = OltSlotSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['enabled', 'availability', 'actual_type', 'olt']
    ordering_fields = ['slot_name', 'actual_type', 'restart_count']


class OltTemperatureListAPIView(generics.ListAPIView):
    """
    Lista temperaturas da OLT
    """
    queryset = OltTemperature.objects.all().order_by('slot_name', 'sensor_id')
    serializer_class = OltTemperatureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['slot_name', 'olt']
    ordering_fields = ['slot_name', 'sensor_id', 'actual_temp']


class OltSfpDiagnosticsListAPIView(generics.ListAPIView):
    """
    Lista diagnósticos SFP da OLT
    """
    queryset = OltSfpDiagnostics.objects.all().order_by('interface')
    serializer_class = OltSfpDiagnosticsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['olt']
    ordering_fields = ['interface', 'temperature', 'tx_power', 'rx_power']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def olt_system_summary(request):
    """
    Resumo do sistema (versão, uptime, slots, temperatura) de cada OLT ativa
    separadamente - usado pelo card "Sistema OLT" do dashboard. Diferente de
    olt_system_stats (contrato congelado de parceiros, que agrega tudo numa
    visão só da "OLT padrão"/rede como um todo), aqui cada OLT aparece numa
    linha própria.
    """
    resumo = []
    for olt in Olt.objects.filter(is_active=True).order_by('name'):
        system_info = OltSystemInfo.objects.filter(olt=olt).first()

        slots = OltSlot.objects.filter(olt=olt)
        total_slots = slots.count()
        operational_slots = slots.filter(
            enabled=True, availability='available', error_status='no-error'
        ).count()

        temps = OltTemperature.objects.filter(olt=olt)
        temp_agg = temps.aggregate(avg_temp=Avg('actual_temp'), max_temp=Max('actual_temp'))

        resumo.append({
            'id': olt.id,
            'name': olt.name,
            'system_info': OltSystemInfoSerializer(system_info).data if system_info else None,
            'slots_total': total_slots,
            'slots_operational': operational_slots,
            'temperature_avg': round(temp_agg['avg_temp'], 1) if temp_agg['avg_temp'] is not None else None,
            'temperature_max': temp_agg['max_temp'],
            'temperature_critical': temps.filter(actual_temp__gte=75).count(),
            'temperature_warning': temps.filter(actual_temp__gte=70, actual_temp__lt=75).count(),
        })

    return Response({'olts': resumo})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def olt_system_stats(request):
    """
    Estatísticas completas do sistema OLT
    """
    try:
        # Informações do sistema - com múltiplas OLTs, mostra a OLT padrão
        # (primeira ativa); slots/temperaturas abaixo continuam agregando
        # todas as OLTs (visão geral da rede).
        from .utils import get_default_olt
        default_olt = get_default_olt()
        system_info = OltSystemInfo.objects.filter(olt=default_olt).first() if default_olt else None


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


def _enqueue_task(request, task_func, menu_item, olt_scoped=False):
    """Dispara uma task em background. Pra tasks que tocam uma OLT
    (olt_scoped=True): se `olt_id` vier no corpo/query string, dispara só
    pra ela; senão, itera todas as OLTs ativas e enfileira um job por OLT
    - fica pronto pra N OLTs sem exigir que o frontend escolha uma."""
    if not olt_scoped:
        job = task_func.delay(user=request.user.username, menu_item=menu_item)
        return Response({'job_id': job.id, 'menu_item': menu_item}, status=status.HTTP_202_ACCEPTED)

    requested_olt_id = request.data.get('olt_id') or request.query_params.get('olt_id')
    if requested_olt_id:
        job = task_func.delay(olt_id=int(requested_olt_id), user=request.user.username, menu_item=menu_item)
        return Response({'job_ids': [job.id], 'menu_item': menu_item}, status=status.HTTP_202_ACCEPTED)

    active_olt_ids = list(Olt.objects.filter(is_active=True).values_list('id', flat=True))
    if not active_olt_ids:
        return Response({'error': 'Nenhuma OLT ativa cadastrada'}, status=status.HTTP_400_BAD_REQUEST)

    jobs = [
        task_func.delay(olt_id=oid, user=request.user.username, menu_item=menu_item)
        for oid in active_olt_ids
    ]
    return Response({'job_ids': [j.id for j in jobs], 'menu_item': menu_item}, status=status.HTTP_202_ACCEPTED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_update_ports(request):
    """Dispara a atualização de ocupação das portas OLT"""
    return _enqueue_task(request, update_port_occupation_task, 'Atualização de Portas', olt_scoped=True)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_update_onus(request):
    """Dispara a atualização das ONUs"""
    return _enqueue_task(request, update_onus_task, 'Atualização de ONUs', olt_scoped=True)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_update_mac(request):
    """Dispara a atualização dos endereços MAC"""
    return _enqueue_task(request, update_mac_task, 'Atualização de MAC', olt_scoped=True)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_sync_clientes(request):
    """Dispara a sincronização de clientes fibra (IXC) - não é por OLT (é um cadastro único no IXC)"""
    return _enqueue_task(request, update_clientes_task, 'Atualização de Clientes Fibra')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_update_all(request):
    """Dispara a sequência completa de atualizações, incluindo dados da OLT"""
    return _enqueue_task(request, comprehensive_update_task, 'Atualizar Todos os Dados Completo', olt_scoped=True)


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
    onu = ONU.objects.filter(pon=f"1/1/{slot}/{port}", position=position).first()
    connector = olt_connector(onu.olt if onu else None)
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
    onu = ONU.objects.filter(pon=f"1/1/{slot}/{port}", position=position).first()
    connector = olt_connector(onu.olt if onu else None)
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
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ONU_ORDERING_FIELDS

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
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['mac', 'serial', 'desc1', 'desc2']
    ordering_fields = ONU_ORDERING_FIELDS


class OnuWithoutMacListAPIView(generics.ListAPIView):
    """ONUs sem MAC cadastrado (mac vazio ou nulo)"""
    serializer_class = ONUSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['serial', 'desc1', 'desc2', 'pon']
    ordering_fields = ONU_ORDERING_FIELDS

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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['vinculado']
    search_fields = ['nome', 'mac', 'endereco']
    ordering_fields = ['nome', 'mac', 'endereco', 'id_caixa_ftth', 'vinculado']


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
    # View manual (não é um ListAPIView) - sem OrderingFilter, valida a
    # allowlist na mão antes de repassar pro order_by().
    ordering = request.GET.get('ordering', '-client_count')
    campos_validos = {'id_caixa_ftth', '-id_caixa_ftth', 'client_count', '-client_count'}
    if ordering not in campos_validos:
        ordering = '-client_count'

    queryset = ClienteFibraIxc.objects.values('id_caixa_ftth').annotate(
        client_count=Count('id_caixa_ftth')
    ).order_by(ordering)

    if search:
        queryset = queryset.filter(id_caixa_ftth__icontains=search)

    paginator = PageNumberPagination()
    paginator.page_size = 50
    page = paginator.paginate_queryset(list(queryset), request)
    return paginator.get_paginated_response(page)