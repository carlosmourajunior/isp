"""
Escrita no IXC: corrige a CTO (id_caixa_ftth) de um cliente fibra
(radpop_radio_cliente_fibra) a partir da vistoria.

Desligada por padrão - só com IXC_PERMITIR_ESCRITA=true no .env.

Por segurança contra a API apagar campos que não forem enviados, o fluxo é:
1. lê o registro completo do cliente no IXC;
2. devolve o registro INTEIRO com só o id_caixa_ftth trocado (PUT .../<recurso>/<id>);
3. lê de novo e compara: se outro campo mudou, a correção fica como 'alerta'
   e o registro original fica salvo em CorrecaoIxc.registro_antes para restaurar.
"""
import base64
import json
import logging
import os

import requests

from .models import ClienteFibraIxc, CorrecaoIxc

logger = logging.getLogger('olt.connector')

RECURSO = 'radpop_radio_cliente_fibra'
# Campos que o próprio IXC atualiza sozinho numa alteração - não são "mudança indevida".
CAMPOS_AUTOMATICOS = {'id_caixa_ftth', 'ultima_atualizacao', 'data_ultima_alteracao', 'ultima_alteracao'}


class EscritaDesligada(Exception):
    pass


def escrita_permitida():
    return os.getenv('IXC_PERMITIR_ESCRITA', '').strip().lower() in ('1', 'true', 'sim', 'yes')


def _headers(acao=None):
    token = os.getenv('IXC_TOKEN', '').encode('utf-8')
    headers = {
        'Authorization': f"Basic {base64.b64encode(token).decode('utf-8')}",
        'Content-Type': 'application/json',
    }
    if acao:
        headers['ixcsoft'] = acao
    return headers


def _url(sufixo=''):
    return f"https://{os.getenv('IXC_HOST')}/webservice/v1/{RECURSO}{sufixo}"


def buscar_por_campo(campo, valor):
    payload = {'qtype': f'{RECURSO}.{campo}', 'query': str(valor), 'oper': '=', 'page': '1', 'rp': '20',
               'sortname': f'{RECURSO}.id', 'sortorder': 'asc'}
    r = requests.post(_url(), data=json.dumps(payload), headers=_headers('listar'), timeout=30)
    r.raise_for_status()
    return r.json().get('registros') or []


def alterar_caixa(serial, cto, usuario, vistoria_porta=None):
    """Troca a CTO do cliente no IXC. Devolve o CorrecaoIxc gravado (status ok/alerta/erro)."""
    if not escrita_permitida():
        raise EscritaDesligada("Escrita no IXC desligada (IXC_PERMITIR_ESCRITA)")

    local = ClienteFibraIxc.objects.filter(mac=serial).first()
    log = CorrecaoIxc(serial=serial, cliente_nome=local.nome if local else '', cto=cto,
                      vistoria_porta=vistoria_porta, usuario=usuario)

    def falhar(mensagem):
        log.status, log.mensagem = 'erro', mensagem
        log.save()
        logger.error(f"IXC: correção de CTO de {serial} falhou: {mensagem}")
        return log

    if not cto.ixc_id:
        return falhar(f"A CTO {cto.descricao} não existe no IXC (só no projeto) - cadastre-a no IXC primeiro.")

    try:
        registros = buscar_por_campo('mac', serial)
    except requests.RequestException as e:
        return falhar(f"Não foi possível ler o cliente no IXC: {e}")
    if len(registros) != 1:
        return falhar(f"Esperava 1 registro com mac={serial} no IXC, achei {len(registros)}.")

    antes = registros[0]
    log.ixc_registro_id = str(antes.get('id', ''))
    log.caixa_antes = str(antes.get('id_caixa_ftth') or '')
    log.registro_antes = antes
    if log.caixa_antes == cto.ixc_id:
        log.status, log.mensagem = 'ok', 'O IXC já estava com essa CTO - nada alterado.'
        log.save()
        _atualizar_local(local, cto)
        return log

    novo = dict(antes)
    novo['id_caixa_ftth'] = cto.ixc_id
    try:
        r = requests.put(_url(f"/{log.ixc_registro_id}"), data=json.dumps(novo), headers=_headers(), timeout=30)
        resposta = r.json() if r.content else {}
    except (requests.RequestException, ValueError) as e:
        return falhar(f"Erro ao enviar a alteração ao IXC: {e}")
    if r.status_code != 200 or resposta.get('type') == 'error':
        return falhar(f"IXC recusou a alteração (HTTP {r.status_code}): {resposta.get('message') or r.text[:300]}")

    try:
        depois_lista = buscar_por_campo('id', log.ixc_registro_id)
    except requests.RequestException as e:
        depois_lista = []
        logger.warning(f"IXC: não consegui reler {serial} após a correção: {e}")
    depois = depois_lista[0] if depois_lista else {}
    log.registro_depois = depois

    if not depois:
        log.status, log.mensagem = 'alerta', 'Alteração enviada, mas não foi possível reler o registro para conferir.'
    elif str(depois.get('id_caixa_ftth') or '') != cto.ixc_id:
        return falhar(f"O IXC respondeu sucesso, mas o registro continua com a caixa {depois.get('id_caixa_ftth')}.")
    else:
        mudaram = sorted(k for k in set(antes) | set(depois)
                         if k not in CAMPOS_AUTOMATICOS and str(antes.get(k)) != str(depois.get(k)))
        log.outros_campos_alterados = mudaram
        if mudaram:
            log.status = 'alerta'
            log.mensagem = (f"CTO corrigida, mas estes campos também mudaram no IXC: {', '.join(mudaram)}. "
                            f"O registro original está salvo nesta correção.")
        else:
            log.status, log.mensagem = 'ok', resposta.get('message') or 'CTO corrigida no IXC.'
    log.save()
    _atualizar_local(local, cto)
    logger.info(f"IXC: CTO de {serial} alterada de {log.caixa_antes or '-'} para {cto.ixc_id} por {usuario} ({log.status})")
    return log


def _atualizar_local(local, cto):
    """Reflete na cópia local na hora (o próximo sync do IXC confirmaria de qualquer jeito)."""
    if local and local.id_caixa_ftth != cto.ixc_id:
        local.id_caixa_ftth = cto.ixc_id
        local.save(update_fields=['id_caixa_ftth'])
