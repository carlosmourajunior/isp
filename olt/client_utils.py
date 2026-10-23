import base64
import json
import logging
import requests
import os
from .models import ONU, ClienteFibraIxc, Cto

logger = logging.getLogger('olt.connector')


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def update_ctos():
    """Sincroniza o cadastro de caixas (rad_caixa_ftth) do IXC em Cto.

    Não toca nos campos que vêm do KMZ (ramal, portas, splitter) nem na OLT.
    Devolve quantas caixas vieram do IXC.
    """
    from django.db import transaction

    registros = _fetch_all_registros('rad_caixa_ftth', 'rad_caixa_ftth.id')
    if not registros:
        logger.error("IXC: rad_caixa_ftth veio vazio - CTOs não atualizadas")
        return 0

    with transaction.atomic():
        # Só as caixas do IXC - as que existem só no KMZ não somem num sync.
        Cto.objects.filter(origem=Cto.ORIGEM_IXC).update(is_active=False)
        for r in registros:
            Cto.objects.update_or_create(
                ixc_id=str(r['id']),
                defaults={
                    'descricao': (r.get('descricao') or '').strip(),
                    'latitude': _to_float(r.get('latitude')),
                    'longitude': _to_float(r.get('longitude')),
                    'capacidade': _to_int(r.get('capacidade')),
                    'status': r.get('status') or '',
                    'id_projeto': str(r.get('id_projeto') or ''),
                    'origem': Cto.ORIGEM_IXC,
                    'is_active': True,
                },
            )
    logger.info(f"IXC: {len(registros)} CTOs sincronizadas")
    return len(registros)


def update_clientes():
    """Função para atualizar a lista de clientes fibra do IXC e atualizar o campo cliente_fibra nas ONUs."""

    # CTOs primeiro (mesmo sync do IXC). Falha aqui não pode impedir o sync de clientes.
    try:
        update_ctos()
    except Exception as e:
        logger.error(f"IXC: falha ao sincronizar CTOs (seguindo com clientes): {e}")

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
                cliente_data = _cliente_data(registro, cliente_lookup.get(registro.get('id_contrato')))
                ClienteFibraIxc.objects.update_or_create(
                    mac=registro['mac'],
                    defaults=cliente_data
                )

        # Remover apenas os que realmente não existem mais
        # (opcional - pode manter histórico marcando como inativo)
        # ClienteFibraIxc.objects.filter(is_active=False).delete()

    marcar_clientes_fibra()

    logger.info("IXC: sincronização de clientes fibra concluída")


def _cliente_data(registro, dados_reais):
    """Registro de radpop_radio_cliente_fibra (+ nome/status do contrato) -> campos de ClienteFibraIxc."""
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
    return {
        'mac': registro['mac'],
        'nome': nome,
        # "nome" em radpop_radio_cliente_fibra é o login PPPoE.
        'login': (registro.get('login') or registro.get('nome') or '')[:255],
        'status_contrato': dados_reais['status_contrato'] if vinculado else '',
        'status_internet': dados_reais['status_internet'] if vinculado else '',
        'id_contrato': registro.get('id_contrato', ''),
        'vinculado': vinculado,
        'latitude': registro.get('latitude', ''),
        'longitude': registro.get('longitude', ''),
        'endereco': endereco,
        'id_caixa_ftth': registro.get('id_caixa_ftth', ''),
        'is_active': True
    }


def _dados_reais(contrato, cliente):
    return {
        'nome': cliente.get('razao', ''),
        'endereco': _formata_endereco(
            cliente.get('endereco', ''),
            cliente.get('numero', ''),
            cliente.get('complemento', ''),
            cliente.get('bairro', ''),
        ),
        'status_contrato': contrato.get('status') or '',
        'status_internet': contrato.get('status_internet') or '',
    }


def _ixc_buscar(recurso, campo, valor):
    """Busca exata (campo = valor) num recurso do IXC. Só leitura."""
    token = os.getenv('IXC_TOKEN', '').encode('utf-8')
    payload = {'qtype': f'{recurso}.{campo}', 'query': str(valor), 'oper': '=', 'page': '1', 'rp': '20',
               'sortname': f'{recurso}.id', 'sortorder': 'asc'}
    headers = {'ixcsoft': 'listar', 'Content-Type': 'application/json',
               'Authorization': f"Basic {base64.b64encode(token).decode('utf-8')}"}
    r = requests.post(f"https://{os.getenv('IXC_HOST')}/webservice/v1/{recurso}", data=json.dumps(payload),
                      headers=headers, timeout=30)
    r.raise_for_status()
    return r.json().get('registros') or []


def atualizar_cliente_fibra_do_ixc(serial):
    """Atualiza do IXC só o cliente fibra deste serial (sem esperar o sync completo).
    Devolve {'encontrado', 'mensagem', 'cliente'}; erro de rede sobe como requests.RequestException."""
    registros = _ixc_buscar('radpop_radio_cliente_fibra', 'mac', serial)
    if not registros:
        n = ClienteFibraIxc.objects.filter(mac=serial, is_active=True).update(is_active=False)
        ONU.objects.filter(serial=serial).update(cliente_fibra=False)
        extra = ' Registro local marcado como removido.' if n else ''
        return {'encontrado': False, 'cliente': None,
                'mensagem': f'Nenhum cliente fibra com mac={serial} no IXC.{extra}'}
    registro = registros[0]
    dados = None
    if registro.get('id_contrato') not in (None, '', '0'):
        contratos = _ixc_buscar('cliente_contrato', 'id', registro['id_contrato'])
        if contratos and contratos[0].get('id_cliente'):
            clientes = _ixc_buscar('cliente', 'id', contratos[0]['id_cliente'])
            if clientes:
                dados = _dados_reais(contratos[0], clientes[0])
    cliente, _ = ClienteFibraIxc.objects.update_or_create(mac=registro['mac'], defaults=_cliente_data(registro, dados))
    ONU.objects.filter(serial=serial).update(cliente_fibra=True)
    aviso = f' Atenção: {len(registros)} registros com esse mac no IXC, usei o primeiro.' if len(registros) > 1 else ''
    return {'encontrado': True, 'cliente': cliente,
            'mensagem': f'Cliente fibra atualizado do IXC: {cliente.nome} ({cliente.login or "sem login"}).{aviso}'}


def marcar_clientes_fibra():
    """Marca ONU.cliente_fibra pelo serial, em lote (mesma regra de
    ONU.update_cliente_fibra_status: só registros ainda presentes no IXC)."""
    ativos = set(ClienteFibraIxc.objects.filter(is_active=True).values_list('mac', flat=True))
    sim = ONU.objects.filter(serial__in=ativos).exclude(cliente_fibra=True).update(cliente_fibra=True)
    nao = ONU.objects.exclude(serial__in=ativos).exclude(cliente_fibra=False).update(cliente_fibra=False)
    logger.info(f"IXC: cliente_fibra marcado em {sim} ONUs e desmarcado em {nao}")
    return sim, nao


def _formata_endereco(*partes):
    """Junta partes de endereço descartando vazios e placeholders numéricos (ex: '0')."""
    return ', '.join(p for p in partes if p and p != '0')


def _build_cliente_lookup():
    """
    Busca cliente_contrato e cliente em bloco no IXC e monta um mapa
    id_contrato -> {'nome', 'endereco', 'status_contrato', 'status_internet'}
    com o nome/endereço reais do cliente (razão social + endereço cadastral)
    e o status do contrato. Não guarda CPF/CNPJ nem
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

        lookup[id_contrato] = _dados_reais(contrato, cliente)
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
