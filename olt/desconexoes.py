"""
Análise de desconexões (tela "Desconexões"). Cruza o IXC (ClienteFibraIxc) com o log da OLT
(OntEvent vindo do syslog e OntSnapshot de cada sync de ONUs), ligados pelo serial da ONU
(ClienteFibraIxc.mac == ONU.serial).

    recorrentes()      clientes que caem quase todo dia (padrão de desconexão diária)
    offline_ativos()   clientes 100% ativos no IXC cuja ONU está offline há mais de N dias
"""
from collections import Counter, defaultdict
from datetime import timedelta
from statistics import median
from zoneinfo import ZoneInfo

from django.db.models import Count, Max, Min
from django.db.models.functions import TruncDate
from django.utils import timezone

from .contrato import STATUS_CONTRATO, STATUS_INTERNET, situacao_contrato
from .models import ONU, ClienteFibraIxc, OntEvent, OntSnapshot

TZ = ZoneInfo('America/Sao_Paulo')

JANELA_PADRAO = 14
MIN_DIAS_PADRAO = 10
DIAS_OFFLINE_PADRAO = 5

# Tipos que significam "ONT saiu do ar". Os eventos 'other' (RDI, nível de sinal) são ruído.
TIPOS_QUEDA = (OntEvent.TYPE_INATIVA, OntEvent.TYPE_DYING_GASP, OntEvent.TYPE_LOS)

# Padrão "desliga à noite": quedas concentradas entre 22h e 6h (horário local).
NOITE_INICIO, NOITE_FIM = 22, 6
PARTICIPACAO_MINIMA = 0.6

CAUSA_ENERGIA = 'energia'
CAUSA_FIBRA = 'fibra'
CAUSA_MISTO = 'misto'
CAUSA_ROTULOS = {
    CAUSA_ENERGIA: 'Energia / equipamento desligado',
    CAUSA_FIBRA: 'Fibra / sinal',
    CAUSA_MISTO: 'Misto',
}


def _clientes_por_serial(serials):
    """serial -> ClienteFibraIxc ativo no IXC (prefere o registro vinculado a contrato)."""
    out = {}
    qs = ClienteFibraIxc.objects.filter(mac__in=list(serials), is_active=True).order_by('vinculado', 'id')
    for c in qs:
        out[c.mac] = c  # os vinculados vêm por último e prevalecem
    return out


def _cliente_dict(c):
    if c is None:
        return {'cliente_nome': '', 'login': '', 'id_contrato': '', 'situacao': 'sem_cliente',
                'situacao_rotulo': 'Sem cadastro no IXC', 'status_contrato': '', 'status_internet': '',
                'endereco': ''}
    codigo, rotulo = situacao_contrato(c)
    contrato = (c.status_contrato or '').upper()
    internet = (c.status_internet or '').upper()
    return {
        'cliente_nome': c.nome,
        'login': c.login,
        'id_contrato': c.id_contrato,
        'situacao': codigo,
        'situacao_rotulo': rotulo,
        'status_contrato': STATUS_CONTRATO.get(contrato, contrato),
        'status_internet': STATUS_INTERNET.get(internet, internet),
        'endereco': c.endereco or '',
    }


def _iso(dt):
    return dt.isoformat() if dt else None


def _historico_eventos():
    return OntEvent.objects.aggregate(m=Min('occurred_at'))['m']


def _perfil(contagem, horas):
    total = sum(contagem.values()) or 1
    energia = contagem.get(OntEvent.TYPE_DYING_GASP, 0) / total
    fibra = (contagem.get(OntEvent.TYPE_INATIVA, 0) + contagem.get(OntEvent.TYPE_LOS, 0)) / total
    if energia >= PARTICIPACAO_MINIMA:
        causa = CAUSA_ENERGIA
    elif fibra >= PARTICIPACAO_MINIMA:
        causa = CAUSA_FIBRA
    else:
        causa = CAUSA_MISTO
    n_horas = sum(horas.values()) or 1
    noite = sum(n for h, n in horas.items() if h >= NOITE_INICIO or h < NOITE_FIM) / n_horas
    return causa, noite >= PARTICIPACAO_MINIMA


def recorrentes(olt_id=None, janela=JANELA_PADRAO, min_dias=MIN_DIAS_PADRAO):
    """Clientes com queda em pelo menos `min_dias` dos últimos `janela` dias."""
    agora = timezone.now()
    # A janela começa na meia-noite local (hoje conta como um dos dias): assim "dias com queda"
    # nunca passa de `janela`.
    hoje = agora.astimezone(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    inicio = hoje - timedelta(days=janela - 1)

    eventos = OntEvent.objects.filter(occurred_at__gte=inicio, event_type__in=TIPOS_QUEDA).exclude(serial='')
    if olt_id:
        eventos = eventos.filter(olt_id=olt_id)

    candidatos = list(
        eventos.filter(is_clear=False)
        .annotate(dia=TruncDate('occurred_at', tzinfo=TZ))
        .values('olt_id', 'serial')
        .annotate(dias=Count('dia', distinct=True), quedas=Count('id'))
        .filter(dias__gte=min_dias)
        .order_by('-dias', '-quedas')
    )

    historico_inicio = _historico_eventos()
    historico_dias = round((agora - historico_inicio).total_seconds() / 86400, 1) if historico_inicio else 0
    base = {
        'gerado_em': _iso(agora), 'janela': janela, 'min_dias': min_dias,
        'historico_dias': historico_dias,
        'historico_curto': historico_dias < janela,
    }
    if not candidatos:
        return {**base, 'total': 0, 'contagem': {}, 'itens': []}

    serials = {c['serial'] for c in candidatos}
    chaves = {(c['olt_id'], c['serial']) for c in candidatos}

    # início e fim de cada queda, na ordem, para medir duração e horário.
    por_chave = defaultdict(list)
    linhas = (
        eventos.filter(serial__in=serials)
        .order_by('occurred_at')
        .values_list('olt_id', 'serial', 'occurred_at', 'event_type', 'is_clear')
    )
    for olt, serial, quando, tipo, fim in linhas:
        if (olt, serial) in chaves:
            por_chave[(olt, serial)].append((quando, tipo, fim))

    clientes = _clientes_por_serial(serials)
    onus = {(o.olt_id, o.serial): o for o in ONU.objects.filter(serial__in=serials).select_related('olt')}

    itens = []
    for c in candidatos:
        chave = (c['olt_id'], c['serial'])
        tipos, horas, duracoes, pendente = Counter(), Counter(), [], {}
        ultima = None
        for quando, tipo, fim in por_chave[chave]:
            if not fim:
                tipos[tipo] += 1
                horas[quando.astimezone(TZ).hour] += 1
                pendente[tipo] = quando
                ultima = quando
            elif tipo in pendente:
                duracoes.append((quando - pendente.pop(tipo)).total_seconds() / 60)
        causa, noturno = _perfil(tipos, horas)
        onu = onus.get(chave)
        itens.append({
            'olt_id': c['olt_id'],
            'olt_nome': onu.olt.name if onu and onu.olt else '',
            'serial': c['serial'],
            'pon': onu.pon if onu else '',
            'position': onu.position if onu else None,
            'estado_atual': onu.oper_state if onu else None,
            **_cliente_dict(clientes.get(c['serial'])),
            'dias_com_queda': c['dias'],
            'quedas': c['quedas'],
            'quedas_por_dia': round(c['quedas'] / c['dias'], 1),
            'tipos': dict(tipos),
            'causa': causa,
            'causa_rotulo': CAUSA_ROTULOS[causa],
            'noturno': noturno,
            'hora_tipica': horas.most_common(1)[0][0] if horas else None,
            'duracao_mediana_min': round(median(duracoes), 1) if duracoes else None,
            'ultima_queda': _iso(ultima),
        })

    contagem = Counter(i['causa'] for i in itens)
    contagem['noturno'] = sum(1 for i in itens if i['noturno'])
    return {**base, 'total': len(itens), 'contagem': dict(contagem), 'itens': itens}


def offline_ativos(olt_id=None, dias_offline=DIAS_OFFLINE_PADRAO, incluir_sem_contrato=False):
    """ONUs offline há mais de `dias_offline` dias cujo cliente está ativo no IXC
    (contrato A e internet A). Com `incluir_sem_contrato`, entram também os registros de
    provisionamento sem contrato vinculado."""
    agora = timezone.now()
    onus = ONU.objects.exclude(oper_state__iexact='up').select_related('olt')
    if olt_id:
        onus = onus.filter(olt_id=olt_id)
    onus = list(onus)

    clientes = _clientes_por_serial({o.serial for o in onus})

    def elegivel(c):
        if c is None:
            return False
        if c.vinculado:
            return (c.status_contrato or '').upper() == 'A' and (c.status_internet or '').upper() == 'A'
        return incluir_sem_contrato

    candidatas = [o for o in onus if elegivel(clientes.get(o.serial))]
    serials = {o.serial for o in candidatas}

    historico_inicio = OntSnapshot.objects.aggregate(m=Min('taken_at'))['m']
    ultimo_up = {}
    ultimo_evento = {}
    if serials:
        ultimo_up = dict(
            OntSnapshot.objects.filter(serial__in=serials, oper_state__iexact='up')
            .values('serial').annotate(t=Max('taken_at')).values_list('serial', 't')
        )
        for serial, quando, tipo in (
            OntEvent.objects.filter(serial__in=serials, event_type__in=TIPOS_QUEDA, is_clear=False)
            .order_by('serial', '-occurred_at').distinct('serial')
            .values_list('serial', 'occurred_at', 'event_type')
        ):
            ultimo_evento[serial] = (quando, tipo)

    itens = []
    for o in candidatas:
        up = ultimo_up.get(o.serial)
        referencia = up or historico_inicio
        if referencia is None:
            continue
        dias = (agora - referencia).total_seconds() / 86400
        if dias < dias_offline:
            continue
        evento = ultimo_evento.get(o.serial)
        if evento is None:
            causa, causa_rotulo = 'sem_evento', 'Sem evento nos logs (caiu antes do histórico)'
        elif evento[1] == OntEvent.TYPE_DYING_GASP:
            causa, causa_rotulo = CAUSA_ENERGIA, CAUSA_ROTULOS[CAUSA_ENERGIA]
        else:
            causa, causa_rotulo = CAUSA_FIBRA, CAUSA_ROTULOS[CAUSA_FIBRA]
        itens.append({
            'olt_id': o.olt_id,
            'olt_nome': o.olt.name if o.olt else '',
            'serial': o.serial,
            'pon': o.pon,
            'position': o.position,
            'estado_atual': o.oper_state,
            'admin_state': o.admin_state,
            **_cliente_dict(clientes[o.serial]),
            'dias_offline': round(dias, 1),
            # Sem nenhum "up" no histórico: os dias são um mínimo (desde o início dos registros).
            'dias_minimo': up is None,
            'ultimo_online': _iso(up),
            'ultima_queda': _iso(evento[0]) if evento else None,
            'ultima_queda_tipo': evento[1] if evento else None,
            'causa': causa,
            'causa_rotulo': causa_rotulo,
        })

    itens.sort(key=lambda i: -i['dias_offline'])
    return {
        'gerado_em': _iso(agora),
        'dias_offline': dias_offline,
        'incluir_sem_contrato': incluir_sem_contrato,
        'historico_desde': _iso(historico_inicio),
        'onus_offline_total': len(onus),
        'total': len(itens),
        'contagem': dict(Counter(i['causa'] for i in itens)),
        'itens': itens,
    }
