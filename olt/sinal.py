"""
Análise de sinal óptico: faixas atuais e variação no período, com um palpite
de onde está o problema quando vários clientes da mesma caixa ou PON variam juntos.

Fontes:
- OntSnapshot: sinal (olt_rx_sig, dBm) de cada ONT a cada atualização de ONUs;
- OntEvent: alarmes de sinal do syslog (sinal baixo, degradado, Tx alto) e quedas;
- CtoInferencia + Cto (KMZ): caixa provável e ramal de cada ONT.

A comparação usa uma referência: a mediana do sinal no período anterior de mesmo
tamanho (ex.: para "último dia", o dia anterior). Sem histórico anterior, usa a
primeira leitura do período.
"""
import statistics
from collections import Counter, defaultdict
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

# Faixas (mesmas da tela e do dashboard): bom >= -27, alerta -27..-29, crítico < -29.
ALERTA = -27.0
CRITICO = -29.0

PERIODOS = {'24h': timedelta(hours=24), '7d': timedelta(days=7)}
LIMIAR_PADRAO_DB = 2.0

# Descrição do alarme vinda da OLT (texto livre, até 50 caracteres) -> categoria.
ALARMES_SINAL = (
    ('signal too low', 'sinal_baixo'),
    ('signal level too low', 'sinal_baixo'),
    ('degrad', 'sinal_degradado'),
    ('tx power', 'tx_alto'),
    ('too high', 'sinal_alto'),
)


def categoria_alarme(alarm_type):
    texto = (alarm_type or '').lower()
    for trecho, categoria in ALARMES_SINAL:
        if trecho in texto:
            return categoria
    return None


# Agrupamento: quantos clientes de um mesmo lugar precisam variar para virar "problema comum".
MIN_AFETADOS_GRUPO = 2
FRACAO_CTO = 0.5     # metade (ou mais) dos clientes da caixa
FRACAO_PON = 0.3     # 30% (ou mais) das ONTs da PON com leitura


def faixa(dbm):
    if dbm is None:
        return 'sem_leitura'
    if dbm < CRITICO:
        return 'critico'
    if dbm <= ALERTA:
        return 'alerta'
    return 'bom'


def resumo_faixas(olt_id=None):
    from olt.models import ONU, OntSnapshot

    qs = ONU.objects.all()
    snaps = OntSnapshot.objects.all()
    if olt_id:
        qs = qs.filter(olt_id=olt_id)
        snaps = snaps.filter(olt_id=olt_id)
    contagem = Counter(faixa(v) for v in qs.values_list('olt_rx_sig', flat=True))
    return {
        'total': sum(contagem.values()),
        'bom': contagem.get('bom', 0),
        'alerta': contagem.get('alerta', 0),
        'critico': contagem.get('critico', 0),
        'sem_leitura': contagem.get('sem_leitura', 0),
        'ultima_coleta': snaps.aggregate(m=Max('taken_at'))['m'],
    }


def classificar(delta, amplitude, limiar):
    if delta is not None and delta <= -limiar:
        return 'piorou'
    if amplitude >= limiar * 1.5:
        return 'oscilando'
    if delta is not None and delta >= limiar:
        return 'melhorou'
    return None


def analisar_series(series, referencias, limiar):
    """Núcleo puro. series: {chave: [(ts, dbm), ...]} no período (ordenado);
    referencias: {chave: [dbm, ...]} do período anterior.
    -> {chave: {...}} só das ONTs que variaram."""
    variaram = {}
    for chave, pontos in series.items():
        valores = [v for _, v in pontos]
        if len(valores) < 2:
            continue
        ref_lista = referencias.get(chave) or []
        referencia = statistics.median(ref_lista) if ref_lista else valores[0]
        atual = valores[-1]
        delta = round(atual - referencia, 1)
        amplitude = round(max(valores) - min(valores), 1)
        tipo = classificar(delta, amplitude, limiar)
        if tipo is None:
            continue
        variaram[chave] = {
            'tipo': tipo,
            'referencia': round(referencia, 1),
            'referencia_periodo_anterior': bool(ref_lista),
            'atual': atual,
            'minimo': min(valores),
            'maximo': max(valores),
            'delta': delta,
            'amplitude': amplitude,
            'leituras': len(valores),
            'faixa_atual': faixa(atual),
        }
    return variaram


def agrupar(itens, total_por_cto, total_por_pon):
    """Palpite de causa comum: vários clientes da mesma caixa ou PON variando juntos."""
    grupos = []
    por_cto = defaultdict(list)
    por_pon = defaultdict(list)
    for item in itens:
        if item['tipo'] == 'melhorou':
            continue
        if item['cto']:
            por_cto[item['cto']['id']].append(item)
        por_pon[(item['olt_id'], item['pon'])].append(item)

    ctos_em_grupo = set()
    for cto_id, afetados in por_cto.items():
        total = total_por_cto.get(cto_id, 0)
        if len(afetados) >= MIN_AFETADOS_GRUPO and total and len(afetados) / total >= FRACAO_CTO:
            ctos_em_grupo.add(cto_id)
            cto = afetados[0]['cto']
            grupos.append({
                'nivel': 'cto',
                'referencia': cto['descricao'],
                'cto_id': cto_id,
                'ramal': cto.get('ramal') or '',
                'pon': afetados[0]['pon'],
                'afetados': len(afetados),
                'total': total,
                'delta_medio': round(statistics.mean(i['delta'] for i in afetados), 1),
                'diagnostico': (f"{len(afetados)} de {total} clientes da caixa {cto['descricao']} variaram juntos: "
                                f"provável problema na própria caixa (splitter, conector de entrada ou fibra que chega nela)."),
                'serials': [i['serial'] for i in afetados],
            })

    for (olt_id, pon), afetados in por_pon.items():
        total = total_por_pon.get((olt_id, pon), 0)
        ctos = {i['cto']['id'] for i in afetados if i['cto']}
        if len(afetados) >= MIN_AFETADOS_GRUPO and len(ctos) >= 2 and total and len(afetados) / total >= FRACAO_PON:
            ramais = sorted({i['cto'].get('ramal') for i in afetados if i['cto'] and i['cto'].get('ramal')})
            onde = f" ({', '.join(ramais)})" if ramais else ''
            grupos.append({
                'nivel': 'pon',
                'referencia': f"PON {pon}",
                'cto_id': None,
                'ramal': ', '.join(ramais),
                'pon': pon,
                'afetados': len(afetados),
                'total': total,
                'delta_medio': round(statistics.mean(i['delta'] for i in afetados), 1),
                'diagnostico': (f"{len(afetados)} de {total} ONTs da PON {pon}{onde}, em {len(ctos)} caixas diferentes, "
                                f"variaram juntas: provável problema antes das caixas (cabo/ramal alimentador, emenda ou "
                                f"splitter primário) ou na porta PON da OLT."),
                'serials': [i['serial'] for i in afetados],
            })

    # Quem não entrou em nenhum grupo: problema individual.
    em_grupo = {s for g in grupos for s in g['serials']}
    for item in itens:
        if item['tipo'] == 'melhorou':
            item['diagnostico'] = 'Sinal melhorou (manutenção/troca recente?).'
        elif item['serial'] in em_grupo:
            item['diagnostico'] = 'Faz parte de um problema comum (ver resumo).'
        else:
            item['diagnostico'] = 'Individual: drop, conector, curvatura da fibra ou a própria ONU do cliente.'
    grupos.sort(key=lambda g: (g['nivel'] != 'pon', -g['afetados']))
    return grupos


def analisar_variacao(olt_id=None, periodo='24h', limiar=LIMIAR_PADRAO_DB, agora=None):
    from olt.models import ClienteFibraIxc, CtoInferencia, OntEvent, OntSnapshot

    agora = agora or timezone.now()
    janela = PERIODOS.get(periodo, PERIODOS['24h'])
    inicio, inicio_ref = agora - janela, agora - 2 * janela

    snaps = OntSnapshot.objects.filter(taken_at__gte=inicio_ref, olt_rx_sig__isnull=False)
    if olt_id:
        snaps = snaps.filter(olt_id=olt_id)
    series, referencias = defaultdict(list), defaultdict(list)
    for olt, pon, pos, serial, ts, dbm in snaps.order_by('taken_at').values_list(
            'olt_id', 'pon', 'position', 'serial', 'taken_at', 'olt_rx_sig'):
        chave = (olt, pon, pos, serial)
        (series if ts >= inicio else referencias)[chave].append((ts, dbm) if ts >= inicio else dbm)
    leituras_no_periodo = sum(len(v) for v in series.values())

    variaram = analisar_series(series, referencias, limiar)

    eventos = OntEvent.objects.filter(occurred_at__gte=inicio)
    if olt_id:
        eventos = eventos.filter(olt_id=olt_id)
    alarmes = defaultdict(Counter)
    for olt, pon, pos, tipo, alarme in eventos.filter(is_clear=False).values_list(
            'olt_id', 'pon', 'position', 'event_type', 'alarm_type'):
        chave = (olt, pon, pos)
        categoria = categoria_alarme(alarme)
        if categoria:
            alarmes[chave][categoria] += 1
        elif tipo in ('los', 'inativa'):
            alarmes[chave]['quedas'] += 1
        elif tipo == 'dying_gasp':
            alarmes[chave]['falta_energia'] += 1

    inferencias = {(i.olt_id, i.serial): i for i in CtoInferencia.objects.select_related('cto_provavel', 'olt')
                   .filter(**({'olt_id': olt_id} if olt_id else {}))}
    clientes = {c.mac: c for c in ClienteFibraIxc.objects.filter(mac__in={k[3] for k in variaram})}

    itens = []
    for (olt, pon, pos, serial), dados in variaram.items():
        inf = inferencias.get((olt, serial))
        cto = inf.cto_provavel if inf and inf.cto_provavel_id and inf.status != 'incerto' else None
        cliente = clientes.get(serial)
        itens.append({
            'serial': serial,
            'olt_id': olt,
            'olt_nome': inf.olt.name if inf else None,
            'pon': pon,
            'position': pos,
            'cliente_nome': cliente.nome if cliente else '',
            'login': (cliente.login or '') if cliente else '',
            'cto': {'id': cto.id, 'descricao': cto.descricao, 'ramal': cto.ramal} if cto else None,
            'alarmes': dict(alarmes.get((olt, pon, pos), {})),
            **dados,
        })

    # Totais para saber se "afetados" é muito ou pouco naquela caixa / PON.
    total_por_cto = Counter(i.cto_provavel_id for i in inferencias.values()
                            if i.cto_provavel_id and i.status != 'incerto')
    total_por_pon = Counter((o, p) for (o, p, _, _) in series)

    grupos = agrupar(itens, total_por_cto, total_por_pon)
    ordem = {'piorou': 0, 'oscilando': 1, 'melhorou': 2}
    itens.sort(key=lambda i: (ordem[i['tipo']], i['delta']))
    return {
        'periodo': periodo,
        'limiar_db': limiar,
        'inicio': inicio,
        'gerado_em': agora,
        'onts_com_leitura': len(series),
        'leituras_no_periodo': leituras_no_periodo,
        'contagem': dict(Counter(i['tipo'] for i in itens)),
        'grupos': grupos,
        'itens': itens,
    }
