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

    # Divisão inteira + 1 (não int(total/100)+1: para total=4598 isso dava
    # int(45.98)+1=46 no log mas range(1, int(45.98+1))=range(1,46) só
    # rodava as páginas 1-45, descartando os últimos ~98 registros).
    total_paginas = int(data['total']) // 100 + 1
    logger.info(f"IXC: sincronizando {data['total']} clientes fibra em {total_paginas} páginas")

    # radpop_radio_cliente_fibra é uma tabela de provisionamento de rede, não
    # de cadastro: "nome" ali é o login PPPoE e o endereço quase sempre vem
    # vazio (", , , "). O nome/endereço reais do cliente vivem em outras
    # duas tabelas do IXC, ligadas por id_contrato -> cliente_contrato ->
    # cliente. Busca as duas em bloco (evita 1 chamada extra por ONU).
    cliente_lookup = _build_cliente_lookup()

    # Usar transação atômica para evitar perda de dados
    from django.db import transaction
    with transaction.atomic():
        # Marcar todos como inativos primeiro
        ClienteFibraIxc.objects.all().update(is_active=False)

        for page in range(1, total_paginas + 1):
            response = search_ixc_page(page)
            if response.status_code != 200:
                raise RuntimeError(
                    f"IXC respondeu {response.status_code} na página {page} de radpop_radio_cliente_fibra: {response.text[:500]}"
                )
            data = response.json()

            for registro in data['registros']:
                dados_reais = cliente_lookup.get(registro.get('id_contrato'))
                vinculado = bool(dados_reais and dados_reais['nome'])
                if vinculado:
                    nome = dados_reais['nome']
                    endereco = dados_reais['endereco']
                else:
                    nome = registro['nome']
                    endereco = _formata_endereco(
                        registro.get('endereco', ''),
                        registro.get('numero', ''),
                        registro.get('bairro', ''),
                    )

                cliente_data = {
                    'mac': registro['mac'],
                    'nome': nome,
                    'id_contrato': registro.get('id_contrato', ''),
                    'vinculado': vinculado,
                    'latitude': registro.get('latitude', ''),
                    'longitude': registro.get('longitude', ''),
                    'endereco': endereco,
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


def _formata_endereco(*partes):
    """Junta partes de endereço descartando vazios e placeholders numéricos (ex: '0')."""
    return ', '.join(p for p in partes if p and p != '0')


def _build_cliente_lookup():
    """
    Busca cliente_contrato e cliente em bloco no IXC e monta um mapa
    id_contrato -> {'nome', 'endereco'} com o nome/endereço reais do
    cliente (razão social + endereço cadastral). Não guarda CPF/CNPJ nem
    nenhum outro dado sensível - só o necessário pra exibição.

    Não persiste nada: é um cache em memória usado só durante o sync.
    """
    try:
        contratos = _fetch_all_registros('cliente_contrato', 'cliente_contrato.id')
        clientes = _fetch_all_registros('cliente', 'cliente.id')
    except Exception as e:
        logger.error(f"Falha ao buscar cliente_contrato/cliente no IXC, mantendo dados de radpop como fallback: {e}")
        return {}

    clientes_por_id = {c['id']: c for c in clientes if c.get('id')}
    logger.info(f"IXC: {len(contratos)} contratos e {len(clientes)} clientes carregados para enriquecer nomes/endereços")

    lookup = {}
    for contrato in contratos:
        id_contrato = contrato.get('id')
        cliente = clientes_por_id.get(contrato.get('id_cliente'))
        if not id_contrato or not cliente:
            continue

        endereco = _formata_endereco(
            cliente.get('endereco', ''),
            cliente.get('numero', ''),
            cliente.get('complemento', ''),
            cliente.get('bairro', ''),
        )
        lookup[id_contrato] = {
            'nome': cliente.get('razao', ''),
            'endereco': endereco,
        }
    return lookup


def _fetch_all_registros(recurso, qtype):
    """Busca todas as páginas de um recurso de listagem do IXC e retorna a lista completa de registros."""
    response = _ixc_list_request(recurso, qtype, page=1)
    if response.status_code != 200:
        logger.error(f"IXC respondeu {response.status_code} na página 1 de {recurso}: {response.text[:500]}")
        return []

    data = response.json()
    total = int(data.get('total', 0) or 0)
    total_paginas = total // 100 + 1
    registros = list(data.get('registros', []))

    for page in range(2, total_paginas + 1):
        response = _ixc_list_request(recurso, qtype, page=page)
        if response.status_code != 200:
            raise RuntimeError(f"IXC respondeu {response.status_code} na página {page} de {recurso}: {response.text[:500]}")
        registros.extend(response.json().get('registros', []))

    return registros


def _ixc_list_request(recurso, qtype, page):
    host = os.getenv('IXC_HOST')
    url = f"https://{host}/webservice/v1/{recurso}"
    token = os.getenv('IXC_TOKEN').encode('utf-8')

    payload = {
        'qtype': qtype,
        'query': '',
        'oper': '>',
        'page': page,
        'rp': '100',
        'sortname': qtype,
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
        logger.error(f"Falha de rede ao chamar o IXC ({recurso}, página {page}): {e}")
        raise

    return response


def search_ixc_page(page):
    return _ixc_list_request('radpop_radio_cliente_fibra', 'radpop_radio_cliente_fibra.id', page)
