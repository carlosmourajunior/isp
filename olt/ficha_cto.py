"""
Ficha da caixa: cada CTO tem UMA vistoria contínua.

Vistoriar de novo uma caixa retoma a mesma ficha, com o que já foi registrado como
ponto de partida (continuação/complemento), em vez de abrir uma vistoria vazia. O
painel da CTO edita a mesma ficha.

Caixas com várias vistorias antigas são juntadas na mais recente, ficando o registro
mais novo de cada porta e de cada cliente (consolidar). Isso acontece ao abrir a ficha
e, de uma vez para todas as caixas, com `manage.py consolidar_vistorias`.
"""
from collections import Counter

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import CtoInferencia, Vistoria, VistoriaPorta


def registros_vigentes(registros):
    """Repassa os registros em ordem e devolve os que continuam valendo.

    -> [(registro, porta_efetiva)]. Regras:
    - registro com porta: substitui o que havia na porta e tira o mesmo cliente de outra porta;
    - cliente sem porta: substitui o registro anterior do cliente, mantendo a porta que ele tinha;
    - sem porta e sem cliente (drop fantasma sem porta): sempre um registro a mais.
    """
    linhas = []                                  # [registro, porta_efetiva]
    for r in registros:
        if r.porta is not None:
            linhas = [x for x in linhas if x[1] != r.porta and not (r.serial and x[0].serial == r.serial)]
            linhas.append([r, r.porta])
        elif r.serial:
            antigo = next((x for x in linhas if x[0].serial == r.serial), None)
            porta = antigo[1] if antigo else None
            if antigo:
                linhas.remove(antigo)
            linhas.append([r, porta])
        else:
            linhas.append([r, None])
    return [(r, p) for r, p in linhas]


@transaction.atomic
def consolidar(cto):
    """Junta as vistorias da caixa na mais recente. -> a ficha (Vistoria) ou None."""
    vistorias = list(Vistoria.objects.filter(cto=cto).order_by('iniciada_em', 'id'))
    if not vistorias:
        return None
    principal = vistorias[-1]
    if len(vistorias) == 1:
        return principal

    registros = list(VistoriaPorta.objects.filter(vistoria__cto=cto).order_by('registrado_em', 'id'))
    vigentes = registros_vigentes(registros)
    ids = [r.id for r, _ in vigentes]
    VistoriaPorta.objects.filter(vistoria__cto=cto).exclude(id__in=ids).delete()
    # update() não mexe no registrado_em: a data de cada registro continua a original.
    for r, porta in vigentes:
        VistoriaPorta.objects.filter(id=r.id).update(vistoria=principal, porta=porta)

    observacoes = [v.observacao for v in vistorias if v.observacao]
    antigas = vistorias[:-1]
    principal.observacao = '\n'.join(dict.fromkeys(observacoes))
    principal.iniciada_em = antigas[0].iniciada_em    # a ficha começou na primeira vistoria
    principal.tecnico = principal.tecnico or next((v.tecnico for v in reversed(antigas) if v.tecnico), '')
    Vistoria.objects.filter(id=principal.id).update(observacao=principal.observacao,
                                                    iniciada_em=principal.iniciada_em, tecnico=principal.tecnico)
    Vistoria.objects.filter(id__in=[v.id for v in antigas]).delete()
    return principal


def _olt_da_cto(cto):
    if cto.olt_id:
        return cto.olt_id
    # CTO sem OLT pelo KMZ: a OLT onde a inferência mais a encontrou.
    mais_comum = Counter(CtoInferencia.objects.filter(Q(cto_provavel=cto) | Q(cto_cadastro=cto))
                         .values_list('olt_id', flat=True)).most_common(1)
    return mais_comum[0][0] if mais_comum else None


def abrir_ficha(cto, usuario, tecnico='', reabrir=True):
    """-> (ficha, criada). reabrir=True: sessão de campo (volta a ficar "em andamento").
    reabrir=False: só para editar pelo painel, sem mudar o estado da ficha."""
    agora = timezone.now()
    v = consolidar(cto)
    if v is None:
        v = Vistoria.objects.create(cto=cto, olt_id=_olt_da_cto(cto), usuario=usuario, tecnico=(tecnico or '')[:150],
                                    sessao_iniciada_em=agora,
                                    finalizada_em=None if reabrir else agora,
                                    observacao='' if reabrir else 'Criada pelo painel da CTO.')
        return v, True
    if reabrir:
        if v.finalizada_em or v.sessao_iniciada_em is None:
            v.sessao_iniciada_em = agora
        v.finalizada_em = None
        if tecnico:
            v.tecnico = tecnico[:150]
        v.usuario = usuario or v.usuario
        if v.olt_id is None:
            v.olt_id = _olt_da_cto(cto)
        v.save(update_fields=['sessao_iniciada_em', 'finalizada_em', 'tecnico', 'usuario', 'olt'])
    return v, False


def tirar_de_outras_caixas(serial, cto, quando=None):
    """O cliente foi registrado nesta caixa: nas fichas de outras caixas ele deixa de constar.
    A porta de lá fica "não identificado" (havia um drop ali que precisa ser conferido)."""
    quando = quando or timezone.now()
    for r in VistoriaPorta.objects.filter(serial=serial, resultado=VistoriaPorta.RESULTADO_CLIENTE) \
            .exclude(vistoria__cto=cto).select_related('vistoria__cto'):
        if r.porta is None:
            r.delete()                      # sem porta não sobra nada a conferir lá
            continue
        nome = r.cliente_nome or serial
        VistoriaPorta.objects.filter(id=r.id).update(
            resultado=VistoriaPorta.RESULTADO_NAO_IDENTIFICADO, serial='', pon='', position=None, cliente_nome='',
            caixa_ixc_no_registro=None,
            observacao=f"{nome} registrado depois na {cto.descricao} em {quando:%d/%m/%Y}"[:255])
