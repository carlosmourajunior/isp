from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend
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
    OltSystemInfoSerializer,
    OltSlotSerializer,
    OltTemperatureSerializer,
    OltSfpDiagnosticsSerializer,
    OltSystemStatsSerializer
)
from .utils import OltSystemCollector


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
def update_olt_system_data(request):
    """
    Atualiza dados do sistema OLT coletando da OLT
    """
    try:
        collector = OltSystemCollector()
        result = collector.collect_all_system_data()
        
        if result:
            return Response({
                'message': 'Dados do sistema OLT atualizados com sucesso',
                'system_info': OltSystemInfoSerializer(result['system_info']).data if result['system_info'] else None,
                'slots_count': result['slots'].count() if result['slots'] else 0,
                'temperatures_count': result['temperatures'].count() if result['temperatures'] else 0
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
            {'error': f'Erro ao obter alertas: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )