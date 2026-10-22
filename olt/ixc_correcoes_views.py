"""
Correções de CTO no IXC: lote e reversão. Endpoints novos (os de
/api/vistorias/correcoes/... continuam como estão):

    GET  /api/ixc/correcoes/?olt=              histórico com "pode reverter" e o que foi revertido
    POST /api/ixc/correcoes/lote/              {itens: [{serial, cto}, ...]} corrige vários de uma vez (staff)
    POST /api/ixc/correcoes/<pk>/reverter/     volta a CTO de antes daquela correção (staff)
"""
from collections import defaultdict

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .ixc_escrita import (EscritaDesligada, NaoReversivel, alterar_caixa, escrita_permitida,
                          motivo_nao_reversivel, reverter_correcao)
from .models import CorrecaoIxc, Cto, VistoriaPorta

LIMITE_LOTE = 100


def _bloqueio(user):
    if not (user.is_staff or user.is_superuser):
        return Response({'error': 'Só administradores podem alterar o IXC.'}, status=status.HTTP_403_FORBIDDEN)
    if not escrita_permitida():
        return Response({'error': 'Escrita no IXC desligada (IXC_PERMITIR_ESCRITA no .env do servidor).'},
                        status=status.HTTP_403_FORBIDDEN)
    return None


def _caixa(ixc_id, ctos):
    if not ixc_id or ixc_id == '0':
        return None
    cto = ctos.get(ixc_id)
    return {'ixc_id': ixc_id, 'id': cto.id if cto else None, 'descricao': cto.descricao if cto else f'ID {ixc_id}'}


def _dict(c, ctos, motivo=None, reversao=None):
    return {
        'id': c.id,
        'tipo': c.tipo,
        'reverte_id': c.reverte_id,
        'serial': c.serial,
        'cliente_nome': c.cliente_nome,
        'caixa_antes': _caixa(c.caixa_antes, ctos),
        'caixa_depois': _caixa(c.caixa_depois or (c.cto.ixc_id if c.cto_id else ''), ctos),
        'usuario': c.usuario,
        'status': c.status,
        'mensagem': c.mensagem,
        'outros_campos_alterados': c.outros_campos_alterados,
        'criado_em': c.criado_em,
        'vistoria_id': c.vistoria_porta.vistoria_id if c.vistoria_porta_id else None,
        'pode_reverter': motivo is None and c.tipo == CorrecaoIxc.TIPO_CORRECAO,
        'motivo_nao_reverter': motivo,
        'revertida': {'id': reversao.id, 'em': reversao.criado_em, 'por': reversao.usuario} if reversao else None,
    }


def _motivos_em_lote(itens):
    """Mesma regra de ixc_escrita.motivo_nao_reversivel, sem uma consulta por linha."""
    seriais = {c.serial for c in itens}
    validas = defaultdict(list)
    for o in CorrecaoIxc.objects.filter(serial__in=seriais).exclude(status='erro').only(
            'id', 'serial', 'criado_em', 'reverte_id', 'tipo'):
        validas[o.serial].append(o)
    motivos, reversoes = {}, {}
    for c in itens:
        rev = next((o for o in validas[c.serial] if o.reverte_id == c.id), None)
        if rev:
            reversoes[c.id] = rev
        if c.tipo != CorrecaoIxc.TIPO_CORRECAO:
            motivos[c.id] = 'Reversão'
            continue
        if c.status == 'erro':
            motivos[c.id] = 'A correção falhou; o IXC não foi alterado.'
            continue
        destino = c.caixa_depois or (c.cto.ixc_id if c.cto_id else '')
        if not c.ixc_registro_id or not destino or c.caixa_antes == destino:
            motivos[c.id] = 'Nada foi alterado no IXC nessa correção.'
        elif rev:
            motivos[c.id] = 'Já revertida.'
        elif any(o.criado_em > c.criado_em and o.reverte_id != c.id for o in validas[c.serial]):
            motivos[c.id] = 'Há uma alteração mais nova para este cliente - reverta a mais recente.'
        else:
            motivos[c.id] = None
    return motivos, reversoes


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def correcoes_historico(request):
    qs = CorrecaoIxc.objects.select_related('cto', 'vistoria_porta', 'vistoria_porta__vistoria')
    if request.GET.get('olt'):
        olt_id = request.GET['olt']
        qs = qs.filter(Q(vistoria_porta__vistoria__olt_id=olt_id) | Q(cto__olt_id=olt_id) |
                       Q(reverte__vistoria_porta__vistoria__olt_id=olt_id) | Q(reverte__cto__olt_id=olt_id))
    itens = list(qs[:200])
    ctos = {c.ixc_id: c for c in Cto.objects.exclude(ixc_id=None)}
    motivos, reversoes = _motivos_em_lote(itens)
    return Response([_dict(c, ctos, motivos.get(c.id), reversoes.get(c.id)) for c in itens])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def correcoes_lote(request):
    bloqueio = _bloqueio(request.user)
    if bloqueio:
        return bloqueio
    itens = request.data.get('itens') or []
    if not isinstance(itens, list) or not itens:
        return Response({'error': 'informe itens: [{serial, cto}]'}, status=status.HTTP_400_BAD_REQUEST)
    if len(itens) > LIMITE_LOTE:
        return Response({'error': f'no máximo {LIMITE_LOTE} por vez'}, status=status.HTTP_400_BAD_REQUEST)

    ctos = {c.id: c for c in Cto.objects.filter(pk__in=[i.get('cto') for i in itens if isinstance(i, dict)])}
    usuario = request.user.get_username()
    feitos, vistos = [], set()
    for item in itens:
        serial = (item.get('serial') or '').strip() if isinstance(item, dict) else ''
        cto = ctos.get(item.get('cto')) if isinstance(item, dict) else None
        if not serial or not cto or serial in vistos:
            continue
        vistos.add(serial)
        porta = (VistoriaPorta.objects.filter(serial=serial, vistoria__cto=cto)
                 .order_by('-vistoria__iniciada_em').first())
        try:
            feitos.append(alterar_caixa(serial, cto, usuario, vistoria_porta=porta))
        except EscritaDesligada as e:
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

    mapa = {c.ixc_id: c for c in Cto.objects.exclude(ixc_id=None)}
    motivos, reversoes = _motivos_em_lote(feitos)
    resultados = [_dict(c, mapa, motivos.get(c.id), reversoes.get(c.id)) for c in feitos]
    return Response({
        'resultados': resultados,
        'ok': sum(1 for c in feitos if c.status == 'ok'),
        'alerta': sum(1 for c in feitos if c.status == 'alerta'),
        'erro': sum(1 for c in feitos if c.status == 'erro'),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def correcao_reverter(request, pk):
    bloqueio = _bloqueio(request.user)
    if bloqueio:
        return bloqueio
    correcao = get_object_or_404(CorrecaoIxc.objects.select_related('cto'), pk=pk)
    try:
        log = reverter_correcao(correcao, request.user.get_username())
    except NaoReversivel as e:
        return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
    except EscritaDesligada as e:
        return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
    ctos = {c.ixc_id: c for c in Cto.objects.exclude(ixc_id=None)}
    codigo = status.HTTP_200_OK if log.status != 'erro' else status.HTTP_502_BAD_GATEWAY
    return Response(_dict(log, ctos, 'Reversão'), status=codigo)
