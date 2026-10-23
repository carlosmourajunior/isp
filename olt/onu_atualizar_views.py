"""
Atualização de UMA ONU sob demanda (menu de ONUs). Endpoint novo:

    POST /api/onus/<pk>/atualizar/   {fonte: 'olt' | 'ixc'}

- olt: relê a PON da ONU na OLT (status, sinal, descrição) e busca o MAC só dela;
- ixc: busca no IXC o cliente fibra com mac = serial da ONU.

Síncrono (uma conexão SSH / três consultas ao IXC): poucos segundos.
"""
import logging

import requests
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .client_utils import atualizar_cliente_fibra_do_ixc
from .models import ONU
from .security import frontend_only
from .serializers import ONUSerializer
from .utils import olt_connector

logger = logging.getLogger('olt.connector')


def _da_olt(onu):
    mensagens = []
    connector = olt_connector(onu.olt)
    net_connect = connector.connect()
    try:
        r = connector.atualizar_pon(onu.pon, net_connect=net_connect)
        if r['aviso']:
            mensagens.append(r['aviso'])
        atual = ONU.objects.filter(olt=onu.olt, pon=onu.pon, position=onu.position).first()
        if atual is None:
            if r['lida']:
                mensagens.append(f'A posição {onu.pon}/{onu.position} não existe mais na OLT - ONU removida do sistema.')
            return None, mensagens
        if atual.serial != onu.serial:
            mensagens.append(f'Agora quem está nessa posição é a ONU {atual.serial} (antes {onu.serial}).')
        if r['lida']:
            mensagens.append(f'Status lido da OLT: admin {atual.admin_state}, oper {atual.oper_state}, '
                             f'sinal {atual.olt_rx_sig if atual.olt_rx_sig is not None else "—"} dBm.')
        if atual.oper_state == 'up':
            mac, comando = connector.mac_da_onu(atual.pon, atual.position, net_connect=net_connect)
            if mac:
                mensagens.append(f'MAC lido: {mac}.')
            else:
                mensagens.append(f'Nenhum MAC na tabela da OLT para essa ONU (comando: {comando}).')
            if (atual.mac or '') != mac:
                atual.mac = mac
                atual.save(update_fields=['mac'])
        elif atual.mac:
            atual.mac = ''
            atual.save(update_fields=['mac'])
            mensagens.append('ONU offline: MAC limpo.')
        else:
            mensagens.append('ONU offline: sem MAC na OLT.')
        return atual, mensagens
    finally:
        connector.disconnect(net_connect)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@frontend_only
def onu_atualizar(request, pk):
    onu = get_object_or_404(ONU.objects.select_related('olt'), pk=pk)
    fonte = request.data.get('fonte')
    if fonte == 'olt':
        if not onu.olt:
            return Response({'error': 'ONU sem OLT associada.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            atual, mensagens = _da_olt(onu)
        except Exception as e:
            logger.error(f"Atualização individual da ONU {onu.pon}/{onu.position} na OLT falhou: {e}")
            return Response({'error': f'Não foi possível ler a OLT: {e}'}, status=status.HTTP_502_BAD_GATEWAY)
    elif fonte == 'ixc':
        try:
            resultado = atualizar_cliente_fibra_do_ixc(onu.serial)
        except requests.RequestException as e:
            return Response({'error': f'Não foi possível consultar o IXC: {e}'}, status=status.HTTP_502_BAD_GATEWAY)
        atual, mensagens = ONU.objects.filter(pk=pk).first(), [resultado['mensagem']]
    else:
        return Response({'error': "fonte deve ser 'olt' ou 'ixc'"}, status=status.HTTP_400_BAD_REQUEST)
    return Response({'onu': ONUSerializer(atual).data if atual else None, 'mensagens': mensagens})
