"""
Caixas do projeto que não estão no IXC (aba "Fora do IXC" da tela de CTOs). Endpoints novos:

    GET  /api/ctos/fora-do-ixc/?olt=&incluir_cd=1   caixas só-KMZ, com a caixa do IXC usada de modelo
                                                     e alerta de possível duplicada
    POST /api/ctos/fora-do-ixc/cadastrar/            {itens: [{cto, descricao}]} cria no IXC (staff)
    POST /api/ctos/fora-do-ixc/vincular/             {cto, ixc_cto} já existe no IXC: junta as duas (staff)
"""
from collections import Counter

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .ixc_caixas import _ixc_com_coordenada, cadastrar, vincular_existente, vizinhas
from .ixc_escrita import EscritaDesligada, escrita_permitida
from .kmz import nome_vazio
from .models import CadastroCaixaIxc, Cto, VistoriaPorta

LIMITE = 50


def _bloqueio(user):
    if not (user.is_staff or user.is_superuser):
        return Response({'error': 'Só administradores podem alterar o IXC.'}, status=status.HTTP_403_FORBIDDEN)
    if not escrita_permitida():
        return Response({'error': 'Escrita no IXC desligada (IXC_PERMITIR_ESCRITA no .env do servidor).'},
                        status=status.HTTP_403_FORBIDDEN)
    return None


def _log_dict(log):
    return {'id': log.id, 'cto_id': log.cto_id, 'descricao': log.descricao, 'ixc_id': log.ixc_id,
            'status': log.status, 'mensagem': log.mensagem, 'usuario': log.usuario, 'criado_em': log.criado_em}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fora_do_ixc(request):
    qs = Cto.objects.select_related('olt').filter(origem=Cto.ORIGEM_KMZ, is_active=True, ixc_id=None)
    if request.GET.get('olt'):
        qs = qs.filter(olt_id=request.GET['olt'])
    if request.GET.get('incluir_cd') not in ('1', 'true'):
        qs = qs.exclude(tipo='CD')
    ctos = list(qs.order_by('ramal', 'descricao'))
    ixc_ctos = _ixc_com_coordenada()
    clientes = Counter(VistoriaPorta.objects.filter(vistoria__cto__in=ctos, resultado='cliente')
                       .values_list('vistoria__cto_id', flat=True))
    ultimos = {}
    for log in CadastroCaixaIxc.objects.filter(cto__in=ctos).order_by('criado_em'):
        ultimos[log.cto_id] = log
    itens = []
    for c in ctos:
        modelo, dist, duplicada = vizinhas(c, ixc_ctos)
        nome = c.kmz_nome if c.kmz_nome and not nome_vazio(c.kmz_nome) else ''
        itens.append({
            'id': c.id, 'descricao': c.descricao, 'nome_sugerido': nome or ('' if c.descricao.startswith('Sem nome') else c.descricao),
            'tipo': c.tipo, 'ramal': c.ramal, 'olt_nome': c.olt.name if c.olt_id else None,
            'latitude': c.latitude, 'longitude': c.longitude, 'portas': c.portas_base, 'ceo': c.kmz_ceo,
            'clientes_na_vistoria': clientes.get(c.id, 0),
            'modelo': {'id': modelo.id, 'descricao': modelo.descricao, 'ixc_id': modelo.ixc_id,
                       'id_projeto': modelo.id_projeto, 'distancia_m': dist} if modelo else None,
            'duplicada': {'id': duplicada.id, 'descricao': duplicada.descricao, 'ixc_id': duplicada.ixc_id}
            if duplicada else None,
            'ultimo_cadastro': _log_dict(ultimos[c.id]) if c.id in ultimos else None,
        })
    estado = {'permitida': escrita_permitida(), 'staff': bool(request.user.is_staff or request.user.is_superuser)}
    return Response({'caixas': itens, 'pode_cadastrar': estado['permitida'] and estado['staff'],
                     'motivo': '' if estado['permitida'] and estado['staff'] else
                     ('Escrita no IXC desligada no servidor (IXC_PERMITIR_ESCRITA).' if not estado['permitida']
                      else 'Só administradores podem alterar o IXC.')})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fora_do_ixc_cadastrar(request):
    bloqueio = _bloqueio(request.user)
    if bloqueio:
        return bloqueio
    itens = request.data.get('itens') or []
    if not isinstance(itens, list) or not itens:
        return Response({'error': 'informe itens: [{cto, descricao}]'}, status=status.HTTP_400_BAD_REQUEST)
    if len(itens) > LIMITE:
        return Response({'error': f'no máximo {LIMITE} por vez'}, status=status.HTTP_400_BAD_REQUEST)
    nomes = [str(i.get('descricao') or '').strip().upper() for i in itens if isinstance(i, dict)]
    repetidos = {n for n in nomes if n and nomes.count(n) > 1}
    if repetidos:
        return Response({'error': f"Nome repetido no lote: {', '.join(sorted(repetidos))}"},
                        status=status.HTTP_400_BAD_REQUEST)
    usuario = request.user.get_username()
    resultados = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        cto = Cto.objects.filter(pk=item.get('cto')).first()
        if cto is None:
            continue
        try:
            resultados.append(_log_dict(cadastrar(cto, usuario, item.get('descricao'))))
        except EscritaDesligada as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
    return Response({'resultados': resultados, **Counter(r['status'] for r in resultados)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fora_do_ixc_vincular(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({'error': 'Só administradores.'}, status=status.HTTP_403_FORBIDDEN)
    cto = get_object_or_404(Cto, pk=request.data.get('cto'), origem=Cto.ORIGEM_KMZ, ixc_id=None)
    ixc_cto = get_object_or_404(Cto, pk=request.data.get('ixc_cto'), origem=Cto.ORIGEM_IXC)
    if not ixc_cto.ixc_id:
        return Response({'error': 'A caixa escolhida não tem id do IXC.'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(_log_dict(vincular_existente(cto, ixc_cto, request.user.get_username())))
