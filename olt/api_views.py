from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import ONU, OltUsers, PlacaOnu, ClienteFibraIxc
from .serializers import (
    ONUSerializer, 
    ONUDetailSerializer,
    OltUsersSerializer, 
    PlacaOnuSerializer, 
    ClienteFibraIxcSerializer
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