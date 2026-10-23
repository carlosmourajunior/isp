"""
Sinal óptico (tela "Sinal óptico"). Endpoints novos:
    GET /api/sinal/resumo/?olt=                         ONTs por faixa de sinal agora
    GET /api/sinal/variacao/?olt=&periodo=24h|7d&limiar=2   quem variou + palpite de causa comum
    GET /api/sinal/caixas/?olt=&limiar=-26               caixas/PONs/ramais com sinal ruim e onde está a perda
    GET /api/sinal/caixas/mapa/?olt=&limiar=-26          o mesmo, com as coordenadas das caixas para o mapa
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .sinal import LIMIAR_PADRAO_DB, PERIODOS, analisar_variacao, resumo_faixas
from .sinal_caixas import LIMIAR_PADRAO, analisar_caixas


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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sinal_caixas(request):
    try:
        limiar = max(-35.0, min(-15.0, float(request.GET.get('limiar', LIMIAR_PADRAO))))
    except ValueError:
        limiar = LIMIAR_PADRAO
    r = analisar_caixas(request.GET.get('olt') or None, limiar)
    r.pop('_caixas')
    for a in r['achados']:
        a.pop('_ctos', None)
    return Response(r)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sinal_caixas_mapa(request):
    """Achados (mesma ordem de /sinal/caixas/) com os ids das caixas de cada um, e as caixas
    das PONs afetadas com coordenadas (inclusive as boas, como referência)."""
    try:
        limiar = max(-35.0, min(-15.0, float(request.GET.get('limiar', LIMIAR_PADRAO))))
    except ValueError:
        limiar = LIMIAR_PADRAO
    r = analisar_caixas(request.GET.get('olt') or None, limiar)
    return Response({
        'limiar': r['limiar'],
        'gerado_em': r['gerado_em'],
        'caixas': r['_caixas'],
        'achados': [{'indice': i, 'nivel': a['nivel'], 'severidade': a['severidade'], 'referencia': a['referencia'],
                     'pon': a['pon'], 'diagnostico': a['diagnostico'], 'ruins': a['ruins'], 'clientes': a['clientes'],
                     'mediana': a['mediana'], 'ctos': a['_ctos']}
                    for i, a in enumerate(r['achados'])],
    })
