"""
Caixas com sinal ruim: onde provavelmente está a perda.

Ideia: o valor absoluto do sinal não diz onde está o problema; a comparação diz.
Clientes da mesma PON passam pelo mesmo caminho até o splitter primário, então:

Padrão da rede: PON -> 1:2 -> 1:8 (na CEO/CD) -> 1:8 (na CTO) = 128 clientes. A CEO de
cada caixa vem do projeto (olt/kmz_topologia.py).

- várias PONs do mesmo cabo de backbone ..... cabo de backbone / CEO de passagem;
- PON inteira baixa ........................ antes das 1:8 de distribuição: 1:2, fibra de
                                              alimentação da CEO, SFP/porta da OLT;
- uma 1:8 de distribuição (CEO) baixa e a
  outra metade da PON boa .................. splitter 1:8 da CEO ou a fusão de entrada dele;
- caixas de um cabo que nasce numa fusão ..... a fusão ou o cabo depois dela;
- um ramal da PON baixo e os outros bons .... cabo/emenda/splitter primário daquele ramal;
- uma caixa baixa e as vizinhas (mesma PON)
  boas, com os clientes dela parecidos entre si ... perda dentro da caixa: splitter da CTO,
                                              conector de entrada ou fusão;
- poucos clientes ruins numa caixa boa ...... drop, conector ou a própria ONU.

Ajustes para não acusar à toa:
- splitter do projeto (KMZ): uma caixa 1:16 perde ~3 dB a mais que uma 1:8 por projeto;
- distância: ~0,35 dB/km (1310 nm, o sinal medido na OLT é o de subida);
- splitter adicionado em campo (cascata) explica clientes bem piores numa caixa.

Tendência: compara com a mediana do mesmo grupo 7-14 dias atrás (OntSnapshot) para
separar "piorou agora" (sujeira, dano, fusão) de "sempre foi assim" (projeto/instalação).
"""
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import timedelta

from django.utils import timezone

LIMIAR_PADRAO = -26.0
DB_POR_KM = 0.35
DELTA_CAIXA = 2.5        # dB pior que as vizinhas (já ajustado) para culpar a caixa
DISPERSAO_MAX = 3.0      # clientes da caixa "parecidos entre si" (desvio entre o melhor e o pior, sem extremos)
FRACAO_RUINS = 0.6       # fração de clientes ruins para considerar a caixa toda ruim
STATUS_COM_CAIXA = ('vistoriado', 'confirmado', 'provavel', 'divergente')


def perda_splitter(texto):
    """'1:8' -> perda típica em dB (10·log10(N) + ~1 dB de excesso)."""
    try:
        n = int(str(texto).split(':')[1])
        return round(10 * math.log10(n) + 1.0, 1) if n > 1 else 0.0
    except (IndexError, ValueError, TypeError):
        return None


def _mediana(valores):
    return round(statistics.median(valores), 1) if valores else None


def _dispersao(valores):
    """Faixa entre o 2º melhor e o 2º pior (um cliente fora da curva não conta)."""
    v = sorted(valores)
    if len(v) >= 4:
        v = v[1:-1]
    return round(v[-1] - v[0], 1) if len(v) >= 2 else 0.0


def analisar(onts, limiar=LIMIAR_PADRAO, historico=None):
    """Núcleo puro.

    onts: [{serial, cliente, olt_id, olt_nome, pon, sinal, ont_rx, distancia,
            cto: {id, descricao, ramal, splitter, portas, extras} | None}]
    historico: {serial: sinal mediano 7-14 dias atrás}
    """
    historico = historico or {}
    por_pon = defaultdict(list)
    for o in onts:
        por_pon[(o['olt_id'], o['pon'])].append(o)

    achados = []
    for (olt_id, pon), lista in por_pon.items():
        sinais = [o['sinal'] for o in lista]
        ruins_pon = [o for o in lista if o['sinal'] < limiar]
        if not ruins_pon:
            continue
        mediana_pon = _mediana(sinais)
        base = {'olt_id': olt_id, 'olt_nome': lista[0]['olt_nome'], 'pon': pon}
        por_cto = defaultdict(list)
        for o in lista:
            por_cto[o['cto']['id'] if o['cto'] else None].append(o)
        ctos_conhecidas = [k for k in por_cto if k is not None]


        # ---- PON inteira baixa: mediana abaixo do limiar e o problema espalhado pela maioria das caixas
        ctos_com_ruins = {o['cto']['id'] for o in ruins_pon if o['cto']}
        espalhado = len(ctos_conhecidas) <= 1 or len(ctos_com_ruins) / len(ctos_conhecidas) >= 0.6
        if len(lista) >= 3 and mediana_pon < limiar and espalhado:
            achados.append({**base, **_grupo(lista, limiar, historico),
                            'nivel': 'pon', 'referencia': f'PON {pon}', 'cto': None, 'ramal': '',
                            'mediana_referencia': None, 'delta': None, 'delta_ajustado': None,
                            'severidade': 'alta',
                            'alimentacao': _mais_comum(o['cto'].get('alimentacao') for o in lista if o['cto']),
                            'diagnostico': _texto_pon(pon, lista, ruins_pon, mediana_pon, limiar)})
            continue

        # ---- metade da PON (uma 1:8 de distribuição) baixa
        ceos_culpadas = set()
        por_ceo = defaultdict(list)
        for o in lista:
            if o['cto'] and o['cto'].get('ceo'):
                por_ceo[o['cto']['ceo']].append(o)
        for ceo, cl in por_ceo.items():
            outros = [o['sinal'] for o in lista if not (o['cto'] and o['cto'].get('ceo') == ceo)]
            ctos_ceo = {o['cto']['id'] for o in cl}
            if len(cl) < 3 or len(ctos_ceo) < 2 or len(outros) < 3:
                continue
            m, mo = _mediana([o['sinal'] for o in cl]), _mediana(outros)
            ruins_ceo = {o['cto']['id'] for o in cl if o['sinal'] < limiar}
            if m < limiar and m - mo <= -DELTA_CAIXA and len(ruins_ceo) / len(ctos_ceo) >= FRACAO_RUINS:
                ceos_culpadas.add(ceo)
                entrada = _mais_comum(o['cto'].get('alimentacao') for o in cl)
                achados.append({**base, **_grupo(cl, limiar, historico),
                                'nivel': 'ceo', 'referencia': f'{ceo} (PON {pon})', 'cto': None, 'ceo': ceo,
                                'ramal': _mais_comum(o['cto'].get('ramal') for o in cl) or '',
                                'mediana_referencia': mo, 'delta': round(m - mo, 1), 'delta_ajustado': round(m - mo, 1),
                                'severidade': 'alta', 'alimentacao': entrada,
                                'diagnostico': (f'As {len(ctos_ceo)} caixas que saem do splitter {ceo} estão '
                                                f'{abs(round(m - mo, 1))} dB abaixo do resto da PON (mediana {m} contra {mo} dBm), '
                                                f'e o resto está bom. A perda está nesse 1:8 de distribuição: o splitter, '
                                                f'a fusão/conector de entrada dele'
                                                f'{" ou a saída da 1:2 que o alimenta" if "1:8 nº" in ceo else ""}.')})

        # ---- caixas de um mesmo cabo que nasce numa fusão
        por_cabo = defaultdict(list)
        for o in lista:
            c = o['cto']
            if c and c.get('ceo') not in ceos_culpadas and 'fusão em' in (c.get('cabo') or ''):
                por_cabo[(c.get('ceo'), c['cabo'])].append(o)
        cabos_culpados = set()
        for (ceo, cabo), cl in por_cabo.items():
            ctos_cabo = {o['cto']['id'] for o in cl}
            irmas = [o['sinal'] for o in lista if o['cto'] and o['cto'].get('ceo') == ceo and o not in cl]
            if len(ctos_cabo) < 2 or len(irmas) < 3:
                continue
            m, mo = _mediana([o['sinal'] for o in cl]), _mediana(irmas)
            if m < limiar and m - mo <= -DELTA_CAIXA:
                cabos_culpados.add((ceo, cabo))
                achados.append({**base, **_grupo(cl, limiar, historico),
                                'nivel': 'cabo', 'referencia': f'{cabo} · {ceo}', 'cto': None, 'ceo': ceo,
                                'ramal': _mais_comum(o['cto'].get('ramal') for o in cl) or '',
                                'mediana_referencia': mo, 'delta': round(m - mo, 1), 'delta_ajustado': round(m - mo, 1),
                                'severidade': 'alta',
                                'diagnostico': (f'As {len(ctos_cabo)} caixas do {cabo} estão {abs(round(m - mo, 1))} dB '
                                                f'abaixo das outras caixas do mesmo splitter ({ceo}). A perda está na fusão '
                                                f'onde esse cabo começa ou no próprio cabo.')})

        # ---- um ramal pior que os outros da mesma PON
        por_ramal = defaultdict(list)
        for o in lista:
            if o['cto'] and o['cto'].get('ramal'):
                por_ramal[o['cto']['ramal']].append(o)
        ramais_culpados = set()
        if len(por_ramal) >= 2:
            for ramal, rl in por_ramal.items():
                outros = [o['sinal'] for r, ol in por_ramal.items() if r != ramal for o in ol]
                m, mo = _mediana([o['sinal'] for o in rl]), _mediana(outros)
                ctos_ramal = {o['cto']['id'] for o in rl}
                if len(rl) >= 3 and len(ctos_ramal) >= 2 and m < limiar and m - mo <= -DELTA_CAIXA \
                        and not {o['cto'].get('ceo') for o in rl} <= ceos_culpadas:
                    ramais_culpados.add(ramal)
                    achados.append({**base, **_grupo(rl, limiar, historico),
                                    'nivel': 'ramal', 'referencia': f'{ramal} (PON {pon})', 'cto': None,
                                    'ramal': ramal, 'mediana_referencia': mo, 'delta': round(m - mo, 1),
                                    'delta_ajustado': round(m - mo, 1), 'severidade': 'alta',
                                    'diagnostico': (f'As {len(ctos_ramal)} caixas do {ramal} estão {abs(round(m - mo, 1))} dB '
                                                    f'abaixo dos outros ramais da mesma PON. A perda está no caminho desse '
                                                    f'ramal: cabo, emenda/caixa de emenda ou splitter primário que o alimenta.')})

        # ---- caixa a caixa
        for cto_id in ctos_conhecidas:
            cl = por_cto[cto_id]
            ruins = [o for o in cl if o['sinal'] < limiar]
            if not ruins:
                continue
            cto = cl[0]['cto']
            if cto.get('ramal') in ramais_culpados or cto.get('ceo') in ceos_culpadas \
                    or (cto.get('ceo'), cto.get('cabo')) in cabos_culpados:
                continue                     # já explicado pelo ramal / CEO / cabo
            vizinhas = [o for k, ol in por_cto.items() if k not in (cto_id, None) for o in ol]
            m = _mediana([o['sinal'] for o in cl])
            mv = _mediana([o['sinal'] for o in vizinhas])
            esperado = 0.0
            ps = perda_splitter(cto.get('splitter'))
            pv = [perda_splitter(o['cto'].get('splitter')) for o in vizinhas]
            pv = [p for p in pv if p is not None]
            if ps is not None and pv:
                esperado = round(ps - statistics.median(pv), 1)
            dist = _mediana([o['distancia'] for o in cl if o['distancia'] is not None])
            dist_v = _mediana([o['distancia'] for o in vizinhas if o['distancia'] is not None])
            ajuste_dist = round((dist - dist_v) * DB_POR_KM, 1) if dist is not None and dist_v is not None else 0.0
            delta = round(m - mv, 1) if mv is not None else None
            delta_aj = round(delta + esperado + ajuste_dist, 1) if delta is not None else None
            dispersao = _dispersao([o['sinal'] for o in cl])
            frac = len(ruins) / len(cl)
            extras = cto.get('extras') or []
            explica = []
            if esperado:
                explica.append(f'splitter {cto["splitter"]} explica {esperado:+g} dB')
            if ajuste_dist:
                explica.append(f'distância explica {ajuste_dist:+g} dB')
            nota_ajuste = f" ({'; '.join(explica)})" if explica else ''

            item = {**base, **_grupo(cl, limiar, historico, so_ruins=False),
                    'referencia': cto['descricao'], 'ramal': cto.get('ramal') or '',
                    'cto': {k: cto.get(k) for k in ('id', 'descricao', 'splitter', 'portas')},
                    'ceo': cto.get('ceo') or '',
                    'mediana_referencia': mv, 'delta': delta, 'delta_ajustado': delta_aj,
                    'esperado_splitter': esperado, 'ajuste_distancia': ajuste_dist,
                    'dispersao': dispersao}

            if len(cl) >= 2 and frac >= FRACAO_RUINS and dispersao <= DISPERSAO_MAX:
                if delta_aj is not None and delta_aj <= -DELTA_CAIXA:
                    item.update(nivel='cto', severidade='alta', diagnostico=(
                        f'Caixa toda baixa e por igual ({len(ruins)} de {len(cl)} clientes, mediana {m} dBm), '
                        f'{abs(delta_aj)} dB pior que as outras caixas da PON{nota_ajuste}. Perda concentrada na '
                        f'caixa: splitter da CTO, conector/adaptador de entrada ou fusão na caixa.'))
                elif delta_aj is None:
                    item.update(nivel='cto', severidade='media', diagnostico=(
                        f'Caixa toda baixa e por igual ({len(ruins)} de {len(cl)} clientes, mediana {m} dBm), mas '
                        f'não há outras caixas identificadas nessa PON para comparar. Pode ser a caixa (splitter/'
                        f'entrada) ou o caminho até ela.'))
                else:
                    item.update(nivel='cto', severidade='baixa', diagnostico=(
                        f'Caixa baixa ({m} dBm), mas parecida com as outras caixas da PON'
                        f'{nota_ajuste}: provavelmente é o orçamento óptico do trecho (distância/divisões), '
                        f'não defeito da caixa.'))
            elif extras and len(cl) >= 2 and frac < FRACAO_RUINS:
                item.update(nivel='clientes', severidade='media', diagnostico=(
                    f'{len(ruins)} de {len(cl)} clientes ruins numa caixa com splitter adicionado em campo '
                    f'({", ".join(f"1:{e}" for e in extras)}). Cliente no splitter em cascata perde 7-10 dB a mais: '
                    f'confira se os ruins estão nele; se estiverem, o splitter extra (ou a fusão dele) é o suspeito.'))
            else:
                item.update(nivel='clientes', severidade='media' if len(ruins) > 1 else 'baixa', diagnostico=(
                    f'{len(ruins)} de {len(cl)} clientes ruins e o resto da caixa bom: problema individual - '
                    f'drop, conector, curvatura da fibra ou a própria ONU.' if len(cl) > 1 else
                    'Único cliente identificado nessa caixa: sem comparação dentro da caixa. '
                    'Se as vizinhas estão boas, o mais provável é drop/conector/ONU.'))
            achados.append(item)

        # ---- ruins sem caixa identificada
        sem = [o for o in por_cto.get(None, []) if o['sinal'] < limiar]
        if sem:
            achados.append({**base, **_grupo(sem, limiar, historico),
                            'nivel': 'sem_caixa', 'referencia': f'PON {pon} - sem caixa identificada', 'cto': None,
                            'ramal': '', 'mediana_referencia': mediana_pon, 'delta': None, 'delta_ajustado': None,
                            'severidade': 'baixa',
                            'diagnostico': 'ONTs com sinal ruim sem caixa provável (inferência incerta). '
                                           'Uma vistoria nessa PON ajuda a localizar.'})

    # ---- várias PONs baixas do mesmo cabo de backbone
    por_backbone = defaultdict(list)
    for a in achados:
        if a['nivel'] == 'pon' and a.get('alimentacao'):
            m = re.search(r'do\s+(\S+)$', a['alimentacao'])
            if m:
                por_backbone[m.group(1)].append(a)
    for cabo, pons in por_backbone.items():
        if len(pons) >= 2:
            achados.append({
                'olt_id': pons[0]['olt_id'], 'olt_nome': pons[0]['olt_nome'], 'pon': ', '.join(a['pon'] for a in pons),
                'nivel': 'backbone', 'referencia': f'Cabo de backbone {cabo}', 'cto': None, 'ceo': '', 'ramal': '',
                'clientes': sum(a['clientes'] for a in pons), 'ruins': sum(a['ruins'] for a in pons),
                'mediana': _mediana([a['mediana'] for a in pons]), 'pior': min(a['pior'] for a in pons),
                'melhor': max(a['melhor'] for a in pons), 'tendencia': None, 'onus': [],
                '_ctos': sorted({i for a in pons for i in a['_ctos']}),
                'mediana_referencia': None, 'delta': None, 'delta_ajustado': None, 'severidade': 'alta',
                'alimentacao': cabo,
                'diagnostico': (f'{len(pons)} PONs alimentadas pelo mesmo cabo {cabo} estão baixas '
                                f'({", ".join(a["pon"] for a in pons)}). Provável problema no cabo de backbone ou numa '
                                f'CEO de passagem dele, antes de chegar nos CDs.')})

    ordem = {'alta': 0, 'media': 1, 'baixa': 2}
    nivel = {'backbone': 0, 'pon': 1, 'ceo': 2, 'ramal': 3, 'cabo': 4, 'cto': 5, 'clientes': 6, 'sem_caixa': 7}
    achados.sort(key=lambda a: (ordem[a['severidade']], nivel[a['nivel']], a['mediana']))
    return achados


def _mais_comum(valores):
    contagem = Counter(v for v in valores if v)
    return contagem.most_common(1)[0][0] if contagem else ''


def _texto_pon(pon, lista, ruins, mediana, limiar):
    ceos = sorted({o['cto']['ceo'] for o in lista if o['cto'] and o['cto'].get('ceo')})
    entrada = _mais_comum(o['cto'].get('alimentacao') for o in lista if o['cto'])
    base = (f'A PON inteira está baixa (mediana {mediana} dBm, {len(ruins)} de {len(lista)} ONTs abaixo de '
            f'{limiar:g})')
    if len(ceos) >= 2:
        base += f', nos dois lados ({", ".join(ceos)})'
    onde = 'o splitter 1:2, ' if any('1:8 nº' in c for c in ceos) else 'o splitter primário, '
    if entrada:
        onde += f'a fibra de alimentação ({entrada}), '
    return (f'{base}. O problema está antes das 1:8 de distribuição: {onde}o cabo até a CEO ou o SFP/porta PON '
            f'da OLT. Comece medindo a potência na saída da OLT e na entrada da CEO.')


def _grupo(lista, limiar, historico, so_ruins=True):
    sinais = [o['sinal'] for o in lista]
    antes = [historico[o['serial']] for o in lista if o['serial'] in historico]
    mediana = _mediana(sinais)
    tendencia = None
    if len(antes) >= max(1, len(lista) // 2):
        variacao = round(mediana - statistics.median(antes), 1)
        tendencia = {'mediana_antes': _mediana(antes), 'variacao': variacao,
                     'texto': (f'piorou {abs(variacao)} dB em relação a 1-2 semanas atrás (problema recente)'
                               if variacao <= -1.5 else
                               'igual a 1-2 semanas atrás (problema antigo: instalação/projeto ou degradação lenta)'
                               if abs(variacao) < 1.5 else f'melhorou {variacao} dB em relação a 1-2 semanas atrás')}
    return {
        '_ctos': sorted({o['cto']['id'] for o in lista if o['cto']}),
        'clientes': len(lista),
        'ruins': sum(1 for s in sinais if s < limiar),
        'mediana': mediana,
        'pior': min(sinais),
        'melhor': max(sinais),
        'tendencia': tendencia,
        'onus': sorted(({k: o[k] for k in ('serial', 'cliente', 'sinal', 'ont_rx', 'distancia')} for o in lista),
                       key=lambda o: o['sinal']),
    }


def analisar_caixas(olt_id=None, limiar=LIMIAR_PADRAO, agora=None):
    from olt.models import ONU, CtoInferencia, OntSnapshot

    agora = agora or timezone.now()
    onus = ONU.objects.select_related('olt').filter(oper_state='up', olt_rx_sig__isnull=False).exclude(olt_rx_sig=0)
    infs = CtoInferencia.objects.select_related('cto_provavel').filter(status__in=STATUS_COM_CAIXA)
    if olt_id:
        onus, infs = onus.filter(olt_id=olt_id), infs.filter(olt_id=olt_id)
    inferencias = {(i.olt_id, i.serial): i for i in infs}

    def distancia(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    onts = []
    for o in onus:
        inf = inferencias.get((o.olt_id, o.serial))
        c = inf.cto_provavel if inf and inf.cto_provavel_id else None
        onts.append({
            'serial': o.serial, 'cliente': (inf.cliente_nome if inf else '') or o.desc1,
            'olt_id': o.olt_id, 'olt_nome': o.olt.name if o.olt else '', 'pon': o.pon,
            'sinal': o.olt_rx_sig, 'ont_rx': o.ont_rx_sig, 'distancia': distancia(o.ont_olt),
            'cto': {'id': c.id, 'descricao': c.descricao, 'ramal': c.ramal, 'splitter': c.kmz_splitter,
                    'portas': c.portas, 'extras': c.splitters_extras, 'ceo': c.kmz_ceo,
                    'alimentacao': c.kmz_alimentacao, 'cabo': c.kmz_cabo} if c else None,
        })

    # Histórico só das PONs que têm alguém ruim (menos consulta).
    pons_ruins = {(o['olt_id'], o['pon']) for o in onts if o['sinal'] < limiar}
    seriais = [o['serial'] for o in onts if (o['olt_id'], o['pon']) in pons_ruins]
    hist = defaultdict(list)
    for serial, v in OntSnapshot.objects.filter(
            serial__in=seriais, taken_at__gte=agora - timedelta(days=14), taken_at__lt=agora - timedelta(days=7),
            olt_rx_sig__isnull=False).values_list('serial', 'olt_rx_sig'):
        hist[serial].append(v)
    historico = {s: statistics.median(v) for s, v in hist.items()}

    achados = analisar(onts, limiar, historico)
    return {
        '_caixas': _caixas_no_mapa(onts, achados, limiar),
        'limiar': limiar,
        'gerado_em': agora,
        'onts_analisadas': len(onts),
        'onts_ruins': sum(1 for o in onts if o['sinal'] < limiar),
        'contagem': {n: sum(1 for a in achados if a['nivel'] == n)
                     for n in ('backbone', 'pon', 'ceo', 'ramal', 'cabo', 'cto', 'clientes', 'sem_caixa')},
        'achados': achados,
    }


def _caixas_no_mapa(onts, achados, limiar):
    """CTOs das PONs com algum achado (as boas também, para dar contexto no mapa)."""
    from olt.models import Cto

    pons = {(a['olt_id'], p.strip()) for a in achados for p in str(a['pon']).split(',')}
    por_cto = defaultdict(list)
    for o in onts:
        if o['cto'] and (o['olt_id'], o['pon']) in pons:
            por_cto[o['cto']['id']].append(o)
    coords = {c.id: c for c in Cto.objects.filter(id__in=por_cto, latitude__isnull=False, longitude__isnull=False)}
    caixas = []
    for cto_id, lista in por_cto.items():
        c = coords.get(cto_id)
        if not c:
            continue
        sinais = [o['sinal'] for o in lista]
        caixas.append({
            'id': cto_id, 'descricao': c.descricao, 'lat': c.latitude, 'lon': c.longitude,
            'ceo': c.kmz_ceo, 'ramal': c.ramal, 'pon': lista[0]['pon'], 'olt_id': lista[0]['olt_id'],
            'clientes': len(lista), 'ruins': sum(1 for v in sinais if v < limiar), 'mediana': _mediana(sinais),
            'pior': min(sinais),
        })
    return caixas
