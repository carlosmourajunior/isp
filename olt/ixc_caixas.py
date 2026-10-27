"""
Cadastro no IXC das caixas que só existem no projeto (KMZ).

O KMZ é o projeto da rede; caixa que está nele e não está no IXC não pode receber
cliente no IXC. Aqui a caixa é criada em rad_caixa_ftth com:
- nome, coordenada e capacidade do sistema (projeto / ajuste de campo);
- projeto, cidade, transmissor, estilo e tipo copiados da caixa do IXC mais próxima
  (as caixas novas caem no mesmo projeto/cidade das vizinhas).

Mesmas travas da correção de clientes (olt/ixc_escrita.py): escrita desligada por padrão
(IXC_PERMITIR_ESCRITA), só staff, relê o registro depois de criar e guarda tudo em
CadastroCaixaIxc. Depois de criada, a caixa do sistema passa a apontar para o id do IXC
(a mesma caixa - vistoria, ajustes e topologia continuam ligados nela).
"""
import json
import logging

import requests
from django.utils import timezone

from .ixc_escrita import EscritaDesligada, _headers, escrita_permitida
from .kmz import haversine_m, normalize_name
from .models import CadastroCaixaIxc, Cto

logger = logging.getLogger('olt.connector')

RECURSO = 'rad_caixa_ftth'
# Copiados da caixa vizinha: dizem a que projeto/cidade/equipamento a caixa pertence.
CAMPOS_DO_MODELO = ('codigo_estilo_caixa', 'id_transmissor', 'id_interface', 'id_projeto', 'id_tecnologia',
                    'id_cidade', 'tipo')
MODELO_MAX_M = 3000          # caixa do IXC usada como modelo tem de estar até aqui
DUPLICADA_COORD_M = 25       # já existe caixa do IXC praticamente no mesmo lugar
DUPLICADA_NOME_M = 300       # mesmo nome perto = provavelmente a mesma caixa


def _url(sufixo=''):
    import os
    return f"https://{os.getenv('IXC_HOST')}/webservice/v1/{RECURSO}{sufixo}"


def buscar(campo, valor):
    payload = {'qtype': f'{RECURSO}.{campo}', 'query': str(valor), 'oper': '=', 'page': '1', 'rp': '20',
               'sortname': f'{RECURSO}.id', 'sortorder': 'desc'}
    r = requests.post(_url(), data=json.dumps(payload), headers=_headers('listar'), timeout=30)
    r.raise_for_status()
    return r.json().get('registros') or []


def _ixc_com_coordenada():
    return [c for c in Cto.objects.filter(origem=Cto.ORIGEM_IXC, is_active=True).exclude(ixc_id=None)
            if c.latitude is not None and c.longitude is not None]


def vizinhas(cto, ixc_ctos=None):
    """-> (modelo, distancia_modelo, duplicada) para uma caixa só-KMZ.
    modelo: caixa do IXC mais próxima (até MODELO_MAX_M). duplicada: caixa do IXC que
    parece ser a mesma (mesmo lugar, ou mesmo nome perto) - aí é vincular, não criar."""
    if cto.latitude is None or cto.longitude is None:
        return None, None, None
    ixc_ctos = _ixc_com_coordenada() if ixc_ctos is None else ixc_ctos
    perto = sorted(((haversine_m(cto.latitude, cto.longitude, c.latitude, c.longitude), c) for c in ixc_ctos),
                   key=lambda x: x[0])
    modelo = next(((d, c) for d, c in perto if d <= MODELO_MAX_M), None)
    nome = normalize_name(cto.kmz_nome or cto.descricao)
    duplicada = next((c for d, c in perto
                      if d <= DUPLICADA_COORD_M or (nome and d <= DUPLICADA_NOME_M and normalize_name(c.descricao) == nome)),
                     None)
    return (modelo[1] if modelo else None), (round(modelo[0]) if modelo else None), duplicada


def _vincular(cto, ixc_id, descricao=None):
    cto.ixc_id = str(ixc_id)
    cto.origem = Cto.ORIGEM_IXC
    if descricao:
        cto.descricao = descricao
    cto.save(update_fields=['ixc_id', 'origem', 'descricao', 'updated_at'])


def cadastrar(cto, usuario, descricao=None):
    """Cria a caixa no IXC. -> CadastroCaixaIxc (status ok/alerta/erro)."""
    if not escrita_permitida():
        raise EscritaDesligada("Escrita no IXC desligada (IXC_PERMITIR_ESCRITA)")
    descricao = (descricao or cto.kmz_nome or cto.descricao or '').strip()[:100]
    log = CadastroCaixaIxc(cto=cto, descricao=descricao, usuario=usuario)

    def falhar(msg):
        log.status, log.mensagem = 'erro', msg
        log.save()
        logger.error(f"IXC: cadastro da caixa {descricao or cto.id} falhou: {msg}")
        return log

    if cto.ixc_id:
        return falhar(f"A caixa já está no IXC (id {cto.ixc_id}).")
    if not descricao or descricao.upper().startswith('SEM NOME'):
        return falhar("Dê um nome para a caixa antes de cadastrar no IXC.")
    if cto.latitude is None or cto.longitude is None:
        return falhar("A caixa não tem coordenada.")
    modelo, _, duplicada = vizinhas(cto)
    if duplicada:
        return falhar(f"Já existe no IXC uma caixa no mesmo lugar ou com o mesmo nome: {duplicada.descricao} "
                      f"(id {duplicada.ixc_id}). Vincule em vez de cadastrar.")
    if modelo is None:
        return falhar(f"Nenhuma caixa do IXC até {MODELO_MAX_M} m para servir de modelo (projeto/cidade).")
    if Cto.objects.filter(origem=Cto.ORIGEM_IXC, is_active=True, descricao__iexact=descricao).exists():
        return falhar(f"Já existe no IXC uma caixa chamada {descricao}. Use outro nome.")

    log.modelo_ixc_id = modelo.ixc_id
    try:
        registros = buscar('id', modelo.ixc_id)
    except requests.RequestException as e:
        return falhar(f"Não foi possível ler a caixa modelo no IXC: {e}")
    if not registros:
        return falhar(f"A caixa modelo {modelo.descricao} (id {modelo.ixc_id}) não foi encontrada no IXC.")
    base = registros[0]

    novo = {campo: base.get(campo, '') for campo in CAMPOS_DO_MODELO}
    novo.update({
        'status': 'A',
        'descricao': descricao,
        'capacidade': str(cto.portas_base or cto.portas or 8),
        'latitude': f"{cto.latitude:.12f}".rstrip('0'),
        'longitude': f"{cto.longitude:.12f}".rstrip('0'),
        'obs_caixa_ftth': f"Cadastrada pelo sistema a partir do projeto (KMZ) em {timezone.now():%d/%m/%Y} por {usuario}.",
        'cep': '', 'endereco': '', 'numero': '', 'bairro': '',
    })
    log.registro_enviado = novo
    try:
        r = requests.post(_url(), data=json.dumps(novo), headers=_headers(), timeout=30)
        resposta = r.json() if r.content else {}
    except (requests.RequestException, ValueError) as e:
        return falhar(f"Erro ao enviar ao IXC: {e}")
    if r.status_code != 200 or resposta.get('type') == 'error':
        return falhar(f"IXC recusou (HTTP {r.status_code}): {resposta.get('message') or r.text[:300]}")

    novo_id = str(resposta.get('id') or '')
    try:
        lidos = buscar('id', novo_id) if novo_id else [x for x in buscar('descricao', descricao)]
    except requests.RequestException as e:
        lidos = []
        logger.warning(f"IXC: não consegui reler a caixa {descricao}: {e}")
    lido = lidos[0] if lidos else {}
    novo_id = novo_id or str(lido.get('id') or '')
    log.registro_lido = lido
    log.ixc_id = novo_id
    if not novo_id:
        log.status = 'alerta'
        log.mensagem = ('O IXC respondeu sucesso, mas não devolveu o id e não achei a caixa pelo nome. '
                        'Confira no IXC; o próximo sync de CTOs traz a caixa.')
        log.save()
        return log

    _vincular(cto, novo_id, descricao)
    diferentes = [c for c in ('descricao', 'capacidade', 'id_projeto', 'id_cidade')
                  if lido and str(lido.get(c, '')) != str(novo.get(c, ''))]
    if not lido:
        log.status, log.mensagem = 'alerta', f'Criada no IXC (id {novo_id}), mas não consegui reler para conferir.'
    elif diferentes:
        log.status, log.mensagem = 'alerta', f"Criada no IXC (id {novo_id}), mas estes campos ficaram diferentes: {', '.join(diferentes)}."
    else:
        log.status, log.mensagem = 'ok', f'Caixa criada no IXC (id {novo_id}).'
    log.save()
    logger.info(f"IXC: caixa {descricao} criada (id {novo_id}) por {usuario}, modelo {modelo.descricao}")
    return log


def vincular_existente(cto, ixc_cto, usuario):
    """A caixa do projeto já existe no IXC (achada como duplicada): junta as duas no sistema.
    A do projeto passa a ser a do IXC; a cópia do IXC que veio no sync é desativada."""
    from .models import CtoInferencia, Vistoria

    log = CadastroCaixaIxc(cto=cto, descricao=ixc_cto.descricao, usuario=usuario, ixc_id=ixc_cto.ixc_id)
    ixc_id = ixc_cto.ixc_id
    # A vistoria, a topologia e os ajustes de campo ficam na caixa do projeto; o que estava na cópia vem junto.
    Vistoria.objects.filter(cto=ixc_cto).update(cto=cto)
    CtoInferencia.objects.filter(cto_provavel=ixc_cto).update(cto_provavel=cto)
    CtoInferencia.objects.filter(cto_cadastro=ixc_cto).update(cto_cadastro=cto)
    CtoInferencia.objects.filter(cto_alternativa=ixc_cto).update(cto_alternativa=cto)
    for campo in ('capacidade', 'status', 'id_projeto'):
        if not getattr(cto, campo, None):
            setattr(cto, campo, getattr(ixc_cto, campo))
    ixc_cto.ixc_id = None
    ixc_cto.is_active = False
    ixc_cto.save(update_fields=['ixc_id', 'is_active', 'updated_at'])
    cto.save(update_fields=['capacidade', 'status', 'id_projeto', 'updated_at'])
    _vincular(cto, ixc_id, ixc_cto.descricao)
    from .ficha_cto import consolidar
    consolidar(cto)
    log.status, log.mensagem = 'ok', f'Vinculada à caixa já existente no IXC ({ixc_cto.descricao}, id {ixc_id}).'
    log.save()
    return log
