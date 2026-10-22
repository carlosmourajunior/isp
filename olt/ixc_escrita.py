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

from .models import ClienteFibraIxc, CorrecaoIxc, Cto

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


class NaoReversivel(Exception):
    pass


def alterar_caixa(serial, cto, usuario, vistoria_porta=None):
    """Troca a CTO do cliente no IXC. Devolve o CorrecaoIxc gravado (status ok/alerta/erro)."""
    if not escrita_permitida():
        raise EscritaDesligada("Escrita no IXC desligada (IXC_PERMITIR_ESCRITA)")
    log = CorrecaoIxc(cto=cto, vistoria_porta=vistoria_porta)
    if not cto.ixc_id:
        log.serial, log.usuario = serial, usuario
        return _falhar(log, f"A CTO {cto.descricao} não existe no IXC (só no projeto) - cadastre-a no IXC primeiro.")
    return _trocar_caixa(log, serial, cto.ixc_id, usuario)


def motivo_nao_reversivel(correcao):
    """None se a correção pode ser desfeita; senão o motivo (para o botão desabilitado)."""
    if correcao.tipo != CorrecaoIxc.TIPO_CORRECAO:
        return 'Reversões não se desfazem - aplique a correção de novo pela vistoria.'
    if correcao.status == 'erro':
        return 'A correção falhou; o IXC não foi alterado.'
    destino = correcao.caixa_depois or (correcao.cto.ixc_id if correcao.cto_id else '')
    if not correcao.ixc_registro_id or not destino or correcao.caixa_antes == destino:
        return 'Nada foi alterado no IXC nessa correção.'
    if any(r.status != 'erro' for r in correcao.reversoes.all()):
        return 'Já revertida.'
    if CorrecaoIxc.objects.filter(serial=correcao.serial, criado_em__gt=correcao.criado_em).exclude(status='erro') \
            .exclude(reverte=correcao).exists():
        return 'Há uma alteração mais nova para este cliente - reverta a mais recente.'
    return None


def reverter_correcao(correcao, usuario):
    """Volta o id_caixa_ftth do cliente para o valor de antes da correção. Só se o IXC
    ainda estiver com a caixa que a correção colocou (se alguém mudou depois, não mexe)."""
    if not escrita_permitida():
        raise EscritaDesligada("Escrita no IXC desligada (IXC_PERMITIR_ESCRITA)")
    motivo = motivo_nao_reversivel(correcao)
    if motivo:
        raise NaoReversivel(motivo)
    destino_antigo = correcao.caixa_depois or correcao.cto.ixc_id
    cto_volta = Cto.objects.filter(ixc_id=correcao.caixa_antes).first() if correcao.caixa_antes else None
    log = CorrecaoIxc(tipo=CorrecaoIxc.TIPO_REVERSAO, reverte=correcao, cto=cto_volta,
                      vistoria_porta=correcao.vistoria_porta)
    return _trocar_caixa(log, correcao.serial, correcao.caixa_antes, usuario, esperado_atual=destino_antigo)


def _falhar(log, mensagem):
    log.status, log.mensagem = 'erro', mensagem
    log.save()
    logger.error(f"IXC: alteração de CTO de {log.serial} falhou: {mensagem}")
    return log


def _trocar_caixa(log, serial, destino, usuario, esperado_atual=None):
    """Fluxo seguro: lê o registro inteiro, troca só id_caixa_ftth, relê e compara."""
    local = ClienteFibraIxc.objects.filter(mac=serial).first()
    log.serial, log.usuario = serial, usuario
    log.cliente_nome = local.nome if local else ''
    log.caixa_depois = destino or ''

    try:
        registros = buscar_por_campo('mac', serial)
    except requests.RequestException as e:
        return _falhar(log, f"Não foi possível ler o cliente no IXC: {e}")
    if len(registros) != 1:
        return _falhar(log, f"Esperava 1 registro com mac={serial} no IXC, achei {len(registros)}.")

    antes = registros[0]
    log.ixc_registro_id = str(antes.get('id', ''))
    log.caixa_antes = str(antes.get('id_caixa_ftth') or '')
    log.registro_antes = antes
    if esperado_atual is not None and log.caixa_antes != esperado_atual:
        return _falhar(log, f"O IXC está com a caixa {log.caixa_antes or '(vazia)'}, não com a {esperado_atual} "
                            f"que a correção colocou: alguém mudou depois. Nada alterado.")
    if log.caixa_antes == log.caixa_depois:
        log.status, log.mensagem = 'ok', 'O IXC já estava com essa CTO - nada alterado.'
        log.save()
        _atualizar_local(local, log.caixa_depois)
        return log

    novo = dict(antes)
    novo['id_caixa_ftth'] = log.caixa_depois
    try:
        r = requests.put(_url(f"/{log.ixc_registro_id}"), data=json.dumps(novo), headers=_headers(), timeout=30)
        resposta = r.json() if r.content else {}
    except (requests.RequestException, ValueError) as e:
        return _falhar(log, f"Erro ao enviar a alteração ao IXC: {e}")
    if r.status_code != 200 or resposta.get('type') == 'error':
        return _falhar(log, f"IXC recusou a alteração (HTTP {r.status_code}): {resposta.get('message') or r.text[:300]}")

    try:
        depois_lista = buscar_por_campo('id', log.ixc_registro_id)
    except requests.RequestException as e:
        depois_lista = []
        logger.warning(f"IXC: não consegui reler {serial} após a alteração: {e}")
    depois = depois_lista[0] if depois_lista else {}
    log.registro_depois = depois

    if not depois:
        log.status, log.mensagem = 'alerta', 'Alteração enviada, mas não foi possível reler o registro para conferir.'
    elif str(depois.get('id_caixa_ftth') or '') != log.caixa_depois:
        return _falhar(log, f"O IXC respondeu sucesso, mas o registro continua com a caixa {depois.get('id_caixa_ftth')}.")
    else:
        mudaram = sorted(k for k in set(antes) | set(depois)
                         if k not in CAMPOS_AUTOMATICOS and str(antes.get(k)) != str(depois.get(k)))
        log.outros_campos_alterados = mudaram
        if mudaram:
            log.status = 'alerta'
            log.mensagem = (f"CTO alterada, mas estes campos também mudaram no IXC: {', '.join(mudaram)}. "
                            f"O registro original está salvo nesta alteração.")
        else:
            acao = 'revertida' if log.tipo == CorrecaoIxc.TIPO_REVERSAO else 'corrigida'
            log.status, log.mensagem = 'ok', resposta.get('message') or f'CTO {acao} no IXC.'
    log.save()
    _atualizar_local(local, log.caixa_depois)
    logger.info(f"IXC: CTO de {serial} alterada de {log.caixa_antes or '-'} para {log.caixa_depois or '-'} "
                f"por {usuario} ({log.tipo}, {log.status})")
    return log


def _atualizar_local(local, ixc_id):
    """Reflete na cópia local na hora (o próximo sync do IXC confirmaria de qualquer jeito)."""
    if local and (local.id_caixa_ftth or '') != (ixc_id or ''):
        local.id_caixa_ftth = ixc_id
        local.save(update_fields=['id_caixa_ftth'])
