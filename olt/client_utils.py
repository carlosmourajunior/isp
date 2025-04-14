import base64
import json
# from .models import ONU, ClienteFibraIxc
import requests
import os
from .models import ONU, ClienteFibraIxc

def update_clientes():
    """Função para atualizar a lista de clientes fibra do IXC e atualizar o campo cliente_fibra nas ONUs."""

    response = search_ixc_page(1)
    # if response.status_code != 200:
    #     print(f"Error: {response.status_code} - {response.text}")
    #     return

    data = response.json()

    total_de_paginas = int(data['total'])/100

    ClienteFibraIxc.objects.all().delete()
    for page in range(1, int(total_de_paginas+1)):
        response = search_ixc_page(page)
        data = response.json()
        
        for registro in data['registros']:
            ClienteFibraIxc.objects.create(
                mac=registro['mac'],
                nome=registro['nome'],
                latitude=registro.get('latitude', ''),
                longitude=registro.get('longitude', ''),
                endereco=f"{registro.get('endereco', '')}, {registro.get('numero', '')}, {registro.get('bairro', '')}, {registro.get('cidade', '')}",
                id_caixa_ftth=registro.get('id_caixa_ftth', '')
            )

    onus = ONU.objects.all()
    for onu in onus:
        onu.update_cliente_fibra_status()


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

    response = requests.post(url, data=json.dumps(payload), headers=headers)

    return response