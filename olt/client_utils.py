import base64
import json
import logging
import requests
import os
from .models import ONU, ClienteFibraIxc

logger = logging.getLogger('olt.connector')


def update_clientes():
    """Função para atualizar a lista de clientes fibra do IXC e atualizar o campo cliente_fibra nas ONUs."""

    response = search_ixc_page(1)
    if response.status_code != 200:
        logger.error(f"IXC respondeu {response.status_code} na página 1 de radpop_radio_cliente_fibra: {response.text[:500]}")
        return

    data = response.json()

    total_de_paginas = int(data['total'])/100
    logger.info(f"IXC: sincronizando {data['total']} clientes fibra em {int(total_de_paginas)+1} páginas")

    # Usar transação atômica para evitar perda de dados
    from django.db import transaction
    with transaction.atomic():
        # Marcar todos como inativos primeiro
        ClienteFibraIxc.objects.all().update(is_active=False)

        for page in range(1, int(total_de_paginas+1)):
            response = search_ixc_page(page)
            if response.status_code != 200:
                raise RuntimeError(
                    f"IXC respondeu {response.status_code} na página {page} de radpop_radio_cliente_fibra: {response.text[:500]}"
                )
            data = response.json()

            for registro in data['registros']:
                cliente_data = {
                    'mac': registro['mac'],
                    'nome': registro['nome'],
                    'latitude': registro.get('latitude', ''),
                    'longitude': registro.get('longitude', ''),
                    'endereco': f"{registro.get('endereco', '')}, {registro.get('numero', '')}, {registro.get('bairro', '')}, {registro.get('cidade', '')}",
                    'id_caixa_ftth': registro.get('id_caixa_ftth', ''),
                    'is_active': True
                }
                ClienteFibraIxc.objects.update_or_create(
                    mac=registro['mac'],
                    defaults=cliente_data
                )
        
        # Remover apenas os que realmente não existem mais
        # (opcional - pode manter histórico marcando como inativo)
        # ClienteFibraIxc.objects.filter(is_active=False).delete()

    onus = ONU.objects.all()
    for onu in onus:
        onu.update_cliente_fibra_status()

    logger.info("IXC: sincronização de clientes fibra concluída")


def search_ixc_page(page):

    host = os.getenv('IXC_HOST')
    url = f"https://{host}/webservice/v1/radpop_radio_cliente_fibra"
    token = os.getenv('IXC_TOKEN').encode('utf-8')

    payload = {
        'qtype': 'radpop_radio_cliente_fibra.id',
        'query': '',
        'oper': '>',
        'page': page,
        'rp': '100',
        'sortname': 'radpop_radio_cliente_fibra.id',
        'sortorder': 'asc'
    }

    headers = {
        'ixcsoft': 'listar',
        'Authorization': 'Basic {}'.
        format(base64.b64encode(token).decode('utf-8')),
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
    except requests.exceptions.RequestException as e:
        logger.error(f"Falha de rede ao chamar o IXC (página {page}): {e}")
        raise

    return response