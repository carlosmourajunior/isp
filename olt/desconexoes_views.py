"""
Análise de desconexões (tela "Desconexões"):
    GET /api/desconexoes/recorrentes/?olt=&janela=14&min_dias=10
    GET /api/desconexoes/offline-ativos/?olt=&dias_offline=5&incluir_sem_contrato=0
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .desconexoes import DIAS_OFFLINE_PADRAO, JANELA_PADRAO, MIN_DIAS_PADRAO, offline_ativos, recorrentes


def _int(request, nome, padrao, minimo, maximo):
    try:
        valor = int(request.GET.get(nome, padrao))
    except (TypeError, ValueError):
        return padrao
    return max(minimo, min(maximo, valor))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def desconexoes_recorrentes(request):
    janela = _int(request, 'janela', JANELA_PADRAO, 3, 30)
    min_dias = _int(request, 'min_dias', MIN_DIAS_PADRAO, 2, janela)
    return Response(recorrentes(request.GET.get('olt') or None, janela, min_dias))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def desconexoes_offline_ativos(request):
    dias = _int(request, 'dias_offline', DIAS_OFFLINE_PADRAO, 1, 365)
    sem_contrato = request.GET.get('incluir_sem_contrato') in ('1', 'true', 'True')
    return Response(offline_ativos(request.GET.get('olt') or None, dias, sem_contrato))
