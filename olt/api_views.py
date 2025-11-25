from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Max, Min, Sum
from .models import (
    ONU, OltUsers, PlacaOnu, ClienteFibraIxc,
    OltSystemInfo, OltSlot, OltTemperature, OltSfpDiagnostics, OltAlarm,
    OrdemServicoIxc
)
from .serializers import (
    ONUSerializer, 
    ONUDetailSerializer,
    OltUsersSerializer, 
    PlacaOnuSerializer, 
    ClienteFibraIxcSerializer,
    OltSystemInfoSerializer,
    OltSlotSerializer,
    OltTemperatureSerializer,
    OltSfpDiagnosticsSerializer,
    OltAlarmSerializer,
    OltSystemStatsSerializer,
    OrdemServicoIxcSerializer,
    OrdemServicoResumoSerializer
)
from .utils import OltSystemCollector
from .security import frontend_only, olt_admin_required


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
    filterset_fields = ['oper_state', 'admin_state', 'cliente_fibra']
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
    Lista ONUs de uma PON específica com paginação
    """
    # Filtrar ONUs da PON específica
    onus = ONU.objects.filter(pon=pon).order_by('position')
    
    # Aplicar filtros adicionais se fornecidos
    oper_state = request.GET.get('oper_state')
    if oper_state:
        onus = onus.filter(oper_state=oper_state)
    
    admin_state = request.GET.get('admin_state')
    if admin_state:
        onus = onus.filter(admin_state=admin_state)
    
    cliente_fibra = request.GET.get('cliente_fibra')
    if cliente_fibra:
        if cliente_fibra.lower() == 'true':
            onus = onus.filter(cliente_fibra=True)
        elif cliente_fibra.lower() == 'false':
            onus = onus.filter(cliente_fibra=False)
    
    # Paginação
    paginator = PageNumberPagination()
    paginator.page_size = 50
    result_page = paginator.paginate_queryset(onus, request)
    
    serializer = ONUSerializer(result_page, many=True)
    
    return paginator.get_paginated_response({
        'pon': pon,
        'total_onus': onus.count(),
        'results': serializer.data
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
    Estatísticas completas do sistema OLT - versão simplificada e segura
    """
    try:
        # Inicializar variáveis básicas
        system_info = OltSystemInfo.objects.first()
        
        # Estatísticas de temperatura (sempre usar dados atuais)
        all_temps = OltTemperature.objects.all()
        critical_temps = all_temps.filter(actual_temp__gte=75).count()
        warning_temps = all_temps.filter(actual_temp__gte=70, actual_temp__lt=75).count()
        normal_temps = all_temps.count() - critical_temps - warning_temps
        
        temp_stats = all_temps.aggregate(
            avg_temp=Avg('actual_temp'),
            max_temp=Max('actual_temp'),
            min_temp=Min('actual_temp')
        )
        
        # Temperaturas por slot
        temp_by_slot = all_temps.values('slot_name').annotate(
            avg_temp=Avg('actual_temp'),
            max_temp=Max('actual_temp'),
            sensor_count=Count('id')
        ).order_by('slot_name')
        
        # Estatísticas dos slots
        total_slots = OltSlot.objects.count()
        operational_slots = OltSlot.objects.filter(
            enabled=True, 
            availability='available', 
            error_status='no-error'
        ).count()
        
        slots_by_type = OltSlot.objects.values('actual_type').annotate(
            count=Count('id')
        ).order_by('actual_type')
        
        # Tentar obter dados do histórico mais recente
        latest_stats = None
        try:
            from olt.models import OltSystemStats
            from olt.serializers import OltSystemStatsHistorySerializer
            latest_stats = OltSystemStats.get_latest()
        except:
            pass  # Se não conseguir obter, usar dados básicos
        
        # Resposta base
        response_data = {
            'system_info': OltSystemInfoSerializer(system_info).data if system_info else None,
            'slots_stats': {
                'total_slots': total_slots,
                'operational_slots': operational_slots,
                'offline_slots': total_slots - operational_slots,
                'slots_by_type': list(slots_by_type),
                'operational_percentage': round((operational_slots / total_slots * 100), 2) if total_slots > 0 else 0
            },
            'temperature_stats': {
                'critical_temperatures': critical_temps,
                'warning_temperatures': warning_temps,
                'normal_temperatures': normal_temps,
                'average_temperature': round(temp_stats['avg_temp'], 1) if temp_stats['avg_temp'] else 0,
                'max_temperature': temp_stats['max_temp'] or 0,
                'min_temperature': temp_stats['min_temp'] or 0,
                'temperature_by_slot': list(temp_by_slot)
            },
            'last_updated': system_info.last_updated if system_info else None
        }
        
        # Adicionar dados do histórico se disponível
        if latest_stats:
            response_data.update({
                'cpu_percent': latest_stats.cpu_percent,
                'cpu_load': latest_stats.cpu_load,
                'mem_percent': latest_stats.mem_percent,
                'model': latest_stats.model,
                'latest_measurement': OltSystemStatsHistorySerializer(latest_stats).data,
                'last_updated': latest_stats.measured_at
            })
        
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def olt_system_history(request):
    """
    Histórico de estatísticas da OLT (últimas 24h ou período específico)
    """
    try:
        from olt.models import OltSystemStats
        from olt.serializers import OltSystemStatsHistorySerializer
        from django.utils import timezone
        from datetime import timedelta
        
        # Parâmetros opcionais
        hours = int(request.GET.get('hours', 24))  # Default: últimas 24h
        limit = int(request.GET.get('limit', 100))  # Default: máximo 100 registros
        
        # Filtrar por período
        if hours > 0:
            cutoff_date = timezone.now() - timedelta(hours=hours)
            queryset = OltSystemStats.objects.filter(measured_at__gte=cutoff_date)
        else:
            queryset = OltSystemStats.objects.all()
        
        # Limitar quantidade e ordenar
        stats = queryset.order_by('-measured_at')[:limit]
        
        response_data = {
            'count': stats.count(),
            'period_hours': hours,
            'measurements': OltSystemStatsHistorySerializer(stats, many=True).data
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao consultar histórico: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def olt_connection_status(request):
    """
    Verifica status de conexão com a OLT
    """
    try:
        # Verificar se temos dados do sistema
        system_info = OltSystemInfo.objects.first()
        
        if system_info:
            return Response({
                'connection_status': 'connected',
                'last_update': system_info.last_updated,
                'system_version': system_info.isam_release,
                'uptime_days': system_info.uptime_days
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def olt_chart_data(request):
    """
    Endpoint para dados dos gráficos de CPU e memória
    Retorna dados formatados para Chart.js
    """
    try:
        from .models import OltSystemStats
        from django.utils import timezone
        from datetime import timedelta
        
        # Buscar dados dos últimos 7 dias
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        
        stats = OltSystemStats.objects.filter(
            measured_at__gte=start_date
        ).order_by('measured_at')
        
        # Preparar dados para o gráfico
        labels = []
        cpu_data = []
        memory_data = []
        
        for stat in stats:
            # Formatar data/hora para o gráfico
            labels.append(stat.measured_at.strftime('%d/%m %H:%M'))
            cpu_data.append(stat.cpu_percent or 0)
            memory_data.append(stat.mem_percent or 0)
        
        # Se não há dados suficientes, criar dados de exemplo/placeholder
        if len(labels) < 2:
            from datetime import datetime, timedelta
            now = datetime.now()
            
            # Criar algumas amostras de exemplo das últimas 24h
            for i in range(24, 0, -1):
                sample_time = now - timedelta(hours=i)
                labels.append(sample_time.strftime('%d/%m %H:%M'))
                # Usar dados das últimas medições ou valores padrão
                last_stats = OltSystemStats.get_latest()
                if last_stats:
                    cpu_data.append(last_stats.cpu_percent or 0)
                    memory_data.append(last_stats.mem_percent or 0)
                else:
                    cpu_data.append(0)
                    memory_data.append(0)
        
        return Response({
            'labels': labels,
            'datasets': [
                {
                    'label': 'CPU (%)',
                    'data': cpu_data,
                    'borderColor': 'rgb(54, 162, 235)',
                    'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                    'borderWidth': 2,
                    'fill': True,
                    'tension': 0.1
                },
                {
                    'label': 'Memória (%)',
                    'data': memory_data,
                    'borderColor': 'rgb(255, 99, 132)',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                    'borderWidth': 2,
                    'fill': True,
                    'tension': 0.1
                }
            ],
            'summary': {
                'current_cpu': cpu_data[-1] if cpu_data else 0,
                'current_memory': memory_data[-1] if memory_data else 0,
                'avg_cpu': sum(cpu_data) / len(cpu_data) if cpu_data else 0,
                'avg_memory': sum(memory_data) / len(memory_data) if memory_data else 0,
                'max_cpu': max(cpu_data) if cpu_data else 0,
                'max_memory': max(memory_data) if memory_data else 0,
                'total_samples': len(labels)
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao obter dados do gráfico: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class OltAlarmListView(generics.ListAPIView):
    """
    API endpoint para listar alarmes da OLT
    """
    serializer_class = OltAlarmSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['alarm_type', 'severity', 'is_active']
    search_fields = ['description', 'entity', 'alarm_id']
    ordering_fields = ['alarm_time', 'collected_at', 'severity']
    ordering = ['-alarm_time', '-collected_at']
    
    def get_queryset(self):
        queryset = OltAlarm.objects.all()
        
        # Filtro para alarmes ativos apenas
        active_only = self.request.query_params.get('active_only', None)
        if active_only == 'true':
            queryset = queryset.filter(is_active=True)
            
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alarms_stats(request):
    """
    Endpoint para estatísticas dos alarmes
    """
    try:
        stats = {
            'total': OltAlarm.objects.count(),
            'active': OltAlarm.objects.filter(is_active=True).count(),
            'by_severity': {
                'critical': OltAlarm.objects.filter(severity='critical', is_active=True).count(),
                'major': OltAlarm.objects.filter(severity='major', is_active=True).count(),
                'minor': OltAlarm.objects.filter(severity='minor', is_active=True).count(),
                'warning': OltAlarm.objects.filter(severity='warning', is_active=True).count(),
            },
            'by_type': {
                'current': OltAlarm.objects.filter(alarm_type='current', is_active=True).count(),
                'major': OltAlarm.objects.filter(alarm_type='major', is_active=True).count(),
                'critical': OltAlarm.objects.filter(alarm_type='critical', is_active=True).count(),
                'log': OltAlarm.objects.filter(alarm_type='log', is_active=True).count(),
            },
            'last_update': OltAlarm.objects.first().collected_at if OltAlarm.objects.exists() else None
        }
        
        return Response(stats)
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao obter estatísticas dos alarmes: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def collect_alarms(request):
    """
    Endpoint para forçar coleta de alarmes
    """
    try:
        from .utils import olt_connector
        
        connector = olt_connector()
        collected_count = connector.collect_all_alarms()
        
        return Response({
            'message': 'Coleta de alarmes iniciada com sucesso',
            'collected_count': collected_count
        })
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao iniciar coleta de alarmes: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =========== ORDENS DE SERVIÇO IXC API VIEWS ===========

class OrdemServicoIxcListAPIView(generics.ListAPIView):
    """
    Lista Ordens de Serviço do IXC com filtros e paginação
    """
    queryset = OrdemServicoIxc.objects.all().order_by('-data_abertura', '-id_ixc')
    serializer_class = OrdemServicoResumoSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'tipo', 'prioridade', 'id_assunto', 'id_tecnico']
    search_fields = ['protocolo', 'assunto_nome', 'tecnico_nome', 'endereco', 'mensagem']
    ordering_fields = ['data_abertura', 'data_agenda', 'data_execucao', 'protocolo', 'valor_total']


class OrdemServicoIxcDetailAPIView(generics.RetrieveAPIView):
    """
    Detalhes de uma Ordem de Serviço específica
    """
    queryset = OrdemServicoIxc.objects.all()
    serializer_class = OrdemServicoIxcSerializer
    permission_classes = [IsAuthenticated]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ordens_servico_stats(request):
    """
    Estatísticas gerais das Ordens de Serviço
    """
    try:
        from django.db.models import Count, Sum, Avg
        from django.utils import timezone
        from datetime import timedelta
        
        # Estatísticas gerais
        total_os = OrdemServicoIxc.objects.count()
        os_abertas = OrdemServicoIxc.objects.filter(status='A').count()
        os_executadas = OrdemServicoIxc.objects.filter(status='X').count()
        os_fechadas = OrdemServicoIxc.objects.filter(status='F').count()
        os_canceladas = OrdemServicoIxc.objects.filter(status='C').count()
        
        # Estatísticas por período
        hoje = timezone.now().date()
        inicio_mes = hoje.replace(day=1)
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        
        os_mes = OrdemServicoIxc.objects.filter(data_abertura__date__gte=inicio_mes).count()
        os_semana = OrdemServicoIxc.objects.filter(data_abertura__date__gte=inicio_semana).count()
        os_hoje = OrdemServicoIxc.objects.filter(data_abertura__date=hoje).count()
        
        # Estatísticas por tipo
        os_por_tipo = OrdemServicoIxc.objects.values('tipo').annotate(
            total=Count('id'),
            tipo_nome=Count('id')  # Será substituído abaixo
        ).order_by('-total')
        
        # Converter códigos de tipo para nomes
        tipos_dict = dict(OrdemServicoIxc.TIPO_CHOICES)
        for item in os_por_tipo:
            item['tipo_nome'] = tipos_dict.get(item['tipo'], item['tipo'])
        
        # Top 5 assuntos
        top_assuntos = OrdemServicoIxc.objects.filter(
            assunto_nome__isnull=False
        ).exclude(
            assunto_nome=''
        ).values('assunto_nome').annotate(
            total=Count('id')
        ).order_by('-total')[:5]
        
        # Valor total das OS em aberto
        valor_total_abertas = OrdemServicoIxc.objects.filter(
            status='A', 
            valor_total__isnull=False
        ).aggregate(total=Sum('valor_total'))['total'] or 0
        
        stats = {
            'total_os': total_os,
            'by_status': {
                'abertas': os_abertas,
                'executadas': os_executadas,
                'fechadas': os_fechadas,
                'canceladas': os_canceladas
            },
            'by_period': {
                'hoje': os_hoje,
                'semana': os_semana,
                'mes': os_mes
            },
            'by_type': list(os_por_tipo),
            'top_assuntos': list(top_assuntos),
            'valor_total_abertas': float(valor_total_abertas),
            'ultima_sincronizacao': OrdemServicoIxc.objects.aggregate(
                ultima=Max('sincronizado_em')
            )['ultima']
        }
        
        return Response(stats)
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao obter estatísticas das OS: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ordens_servico_grafico_dados(request):
    """
    Dados para gráfico de OS por mês e assunto
    """
    try:
        from django.db.models import Count, Sum
        from django.db.models.functions import TruncMonth
        
        # Parâmetros opcionais
        meses_limite = int(request.GET.get('meses', 12))  # Últimos 12 meses por padrão
        top_assuntos = int(request.GET.get('top_assuntos', 10))  # Top 10 assuntos
        
        # Filtrar por data se especificado
        queryset = OrdemServicoIxc.objects.filter(data_abertura__isnull=False)
        
        if meses_limite:
            from django.utils import timezone
            from datetime import timedelta
            data_limite = timezone.now() - timedelta(days=meses_limite * 30)
            queryset = queryset.filter(data_abertura__gte=data_limite)
        
        # Agrupar por mês e assunto
        dados_grafico = queryset.annotate(
            mes=TruncMonth('data_abertura')
        ).values(
            'mes', 'assunto_nome'
        ).annotate(
            total_os=Count('id'),
            os_abertas=Count('id', filter=Q(status='A')),
            os_fechadas=Count('id', filter=Q(status='F')),
            os_executadas=Count('id', filter=Q(status='X')),
            valor_total=Sum('valor_total')
        ).filter(
            assunto_nome__isnull=False
        ).exclude(
            assunto_nome=''
        ).order_by('mes', '-total_os')
        
        # Converter para formato adequado para gráfico
        dados_formatados = []
        for item in dados_grafico:
            dados_formatados.append({
                'mes': item['mes'].strftime('%Y-%m') if item['mes'] else None,
                'mes_nome': item['mes'].strftime('%B %Y') if item['mes'] else None,
                'assunto_nome': item['assunto_nome'] or 'Sem Assunto',
                'total_os': item['total_os'],
                'os_abertas': item['os_abertas'],
                'os_fechadas': item['os_fechadas'],
                'os_executadas': item['os_executadas'],
                'valor_total': float(item['valor_total']) if item['valor_total'] else 0
            })
        
        # Obter lista dos principais assuntos para filtrar
        principais_assuntos = list(
            OrdemServicoIxc.objects.filter(
                assunto_nome__isnull=False
            ).exclude(
                assunto_nome=''
            ).values('assunto_nome').annotate(
                total=Count('id')
            ).order_by('-total')[:top_assuntos].values_list('assunto_nome', flat=True)
        )
        
        # Filtrar apenas os principais assuntos
        dados_filtrados = [
            item for item in dados_formatados 
            if item['assunto_nome'] in principais_assuntos
        ]
        
        return Response({
            'dados': dados_filtrados,
            'principais_assuntos': principais_assuntos,
            'total_registros': len(dados_filtrados),
            'parametros': {
                'meses_limite': meses_limite,
                'top_assuntos': top_assuntos
            }
        })
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao obter dados do gráfico: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
@olt_admin_required
def sincronizar_ordens_servico(request):
    """
    Endpoint para sincronizar Ordens de Serviço do IXC
    """
    try:
        from .client_utils import IxcOSClient
        from django_rq import get_queue
        
        # Parâmetros opcionais
        limite_paginas = request.data.get('limite_paginas', 10)  # Aumentado padrão
        sync_all = request.data.get('sync_all', False)  # Sincronização completa
        
        # Verificar se já existe uma sincronização em andamento
        queue = get_queue('default')
        
        # Determinar timeout baseado no tipo de sync
        timeout = 3600 if sync_all else 1800  # 1 hora para sync completo, 30 min para limitado
        
        # Executar em background
        job = queue.enqueue(
            'olt.tasks.sincronizar_os_task',
            limite_paginas=limite_paginas,
            sync_all=sync_all,
            user=request.user.username,
            job_timeout=timeout
        )
        
        return Response({
            'message': 'Sincronização de OS iniciada com sucesso',
            'job_id': job.id,
            'limite_paginas': limite_paginas,
            'sync_all': sync_all,
            'timeout': timeout,
            'aviso': 'Sincronização completa pode demorar mais de 1 hora' if sync_all else None
        })
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao iniciar sincronização de OS: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )