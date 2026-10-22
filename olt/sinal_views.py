"""
Sinal óptico (tela "Sinal óptico"). Endpoints novos:
    GET /api/sinal/resumo/?olt=                         ONTs por faixa de sinal agora
    GET /api/sinal/variacao/?olt=&periodo=24h|7d&limiar=2   quem variou + palpite de causa comum
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .sinal import LIMIAR_PADRAO_DB, PERIODOS, analisar_variacao, resumo_faixas


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sinal_resumo(request):
    return Response(resumo_faixas(request.GET.get('olt') or None))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sinal_variacao(request):
    periodo = request.GET.get('periodo') if request.GET.get('periodo') in PERIODOS else '24h'
    try:
        limiar = max(0.5, min(10.0, float(request.GET.get('limiar', LIMIAR_PADRAO_DB))))
    except ValueError:
        limiar = LIMIAR_PADRAO_DB
    return Response(analisar_variacao(request.GET.get('olt') or None, periodo, limiar))
