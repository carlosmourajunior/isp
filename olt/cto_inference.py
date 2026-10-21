"""
Inferência de CTO por ONT: cruza o que a rede mostra com o cadastro.

Sinais (cada um soma ou tira pontos de uma CTO candidata):
- Cadastro IXC (ClienteFibraIxc.id_caixa_ftth): ponto de partida, desatualizado.
- PON: uma CTO é alimentada por uma PON. A PON de cada CTO (e de cada ramal do
  KMZ) é aprendida das "âncoras" - ONTs cujo cliente tem CTO no cadastro.
- Distância óptica (ont-olt-distance, resolução 0,1 km): clientes da mesma CTO
  ficam numa faixa estreita.
- Geografia: cliente com lat/long perto da CTO.
- Quedas simultâneas (OntEvent): ONTs que caem juntas compartilham fibra.

O núcleo (infer) é puro - recebe listas e devolve resultados - para ser
testável sem banco. run_inference() carrega do banco e grava CtoInferencia.
"""
import logging
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace

from olt.kmz import haversine_m

logger = logging.getLogger(__name__)

# Pesos e limites - ajustar com o resultado de campo.
W_CADASTRO = 3.0
W_PON_CTO = 2.0          # PON da ONT = PON aprendida da própria CTO
W_PON_RAMAL = 1.0        # PON da ONT = PON aprendida do ramal (CTO sem âncora própria)
PENALTY_PON = -4.0       # PON diferente da CTO, com 2+ outras âncoras sustentando a PON dela
PENALTY_PON_FRACA = -2.0  # PON diferente, mas só 1 âncora sustenta a PON da CTO
PENALTY_PON_RAMAL = -2.0  # PON diferente do ramal (estimativa - ramal pode ter PON minoritária)
W_DIST_MAX = 2.0
DIST_STEP_KM = 0.1       # resolução da OLT
PENALTY_DIST = -2.0      # muito fora da faixa da CTO
DIST_FAR_KM = 0.5
GEO_CANDIDATE_M = 300    # CTO perto do cliente vira candidata mesmo sem PON conhecida
PENALTY_GEO_FAR = -2.0
GEO_FAR_M = 600
W_COFALHA_POR_QUEDA = 0.5
W_COFALHA_MAX = 3.0
BURST_WINDOW_S = 3       # eventos da mesma PON até 3 s de distância = mesma queda
BURST_MAX_FRACAO_PON = 0.5   # queda de mais da metade da PON (problema na PON inteira) não diz nada sobre CTO
INSTAVEL_MAX_QUEDAS = 30     # ONT que cai mais que isso no período é instável: cai junto com todo mundo por acaso
RAMAL_PON_MIN_ANCORAS = 2
RAMAL_PON_MIN_FRACAO = 0.15

CONFIRMADO_MIN = 4.0
PROVAVEL_MIN = 3.0
PROVAVEL_MARGEM = 1.0
DIVERGENTE_MARGEM = 2.0


@dataclass
class Ont:
    pon: str
    position: int
    serial: str
    distance_km: float = None
    cliente_nome: str = ''
    cto_cadastro: object = None      # Cto ou None
    lat: float = None
    lon: float = None


@dataclass
class CtoPerfil:
    cto: object
    pons: Counter = field(default_factory=Counter)     # PON -> nº de âncoras
    distancias: list = field(default_factory=list)

    @property
    def pon_principal(self):
        return self.pons.most_common(1)[0][0] if self.pons else None

    @property
    def distancia_mediana(self):
        return statistics.median(self.distancias) if self.distancias else None

    def sem(self, ont):
        """Perfil sem a própria ONT (leave-one-out): uma âncora não pode ser
        evidência de si mesma."""
        pons = Counter(self.pons)
        pons[ont.pon] -= 1
        pons = +pons  # remove zeros
        distancias = list(self.distancias)
        if ont.distance_km is not None and ont.distance_km in distancias:
            distancias.remove(ont.distance_km)
        return replace(self, pons=pons, distancias=distancias)


def aprender_perfis(onts):
    """Âncoras (ONT com CTO no cadastro) -> perfil por CTO e PONs por ramal."""
    perfis = {}
    ramal_pons = defaultdict(Counter)
    for ont in onts:
        cto = ont.cto_cadastro
        if cto is None:
            continue
        perfil = perfis.setdefault(cto.pk, CtoPerfil(cto))
        perfil.pons[ont.pon] += 1
        if ont.distance_km is not None:
            perfil.distancias.append(ont.distance_km)
        if getattr(cto, 'ramal', ''):
            ramal_pons[(cto.olt_id, cto.ramal)][ont.pon] += 1

    pons_por_ramal = {}
    for chave, contagem in ramal_pons.items():
        total = sum(contagem.values())
        pons_por_ramal[chave] = {pon for pon, n in contagem.items()
                                 if n >= RAMAL_PON_MIN_ANCORAS and n / total >= RAMAL_PON_MIN_FRACAO}
    return perfis, pons_por_ramal


def detectar_quedas(eventos, onts_por_pon):
    """Eventos (pon, position, timestamp) -> lista de quedas: conjuntos de
    posições da mesma PON que caíram juntas (até BURST_WINDOW_S entre eventos).
    ONTs instáveis (mais de INSTAVEL_MAX_QUEDAS eventos) ficam de fora."""
    por_ont = Counter((pon, position) for pon, position, _ in eventos)
    instaveis = {chave for chave, n in por_ont.items() if n > INSTAVEL_MAX_QUEDAS}
    por_pon = defaultdict(list)
    for pon, position, ts in eventos:
        if (pon, position) in instaveis:
            continue
        por_pon[pon].append((ts, position))

    quedas = []
    for pon, lista in por_pon.items():
        lista.sort()
        atual, ultimo = set(), None
        for ts, position in lista:
            if ultimo is not None and (ts - ultimo).total_seconds() > BURST_WINDOW_S:
                quedas.append((pon, atual))
                atual = set()
            atual.add(position)
            ultimo = ts
        if atual:
            quedas.append((pon, atual))

    uteis = []
    for pon, posicoes in quedas:
        total_pon = onts_por_pon.get(pon, 0)
        if len(posicoes) < 2:
            continue
        if total_pon and len(posicoes) / total_pon > BURST_MAX_FRACAO_PON:
            continue
        uteis.append((pon, posicoes))
    return uteis


def contar_cofalhas(quedas, ancoras_por_posicao):
    """-> {(pon, position): Counter(cto_pk -> nº de quedas junto com âncoras dessa CTO)}"""
    cofalhas = defaultdict(Counter)
    for pon, posicoes in quedas:
        ctos_na_queda = Counter(ancoras_por_posicao[(pon, p)] for p in posicoes if (pon, p) in ancoras_por_posicao)
        for p in posicoes:
            propria = ancoras_por_posicao.get((pon, p))
            for cto_pk, n in ctos_na_queda.items():
                # Não conta a própria âncora como evidência dela mesma.
                if cto_pk == propria and n == 1:
                    continue
                cofalhas[(pon, p)][cto_pk] += 1
    return cofalhas


def pontuar(ont, cto, perfil, pons_ramal, cofalhas_ont):
    score, motivos = 0.0, []

    if ont.cto_cadastro is not None and ont.cto_cadastro.pk == cto.pk:
        score += W_CADASTRO
        motivos.append(f"cadastro IXC (+{W_CADASTRO:g})")

    pons_cto = set(perfil.pons) if perfil else set()
    if pons_cto:
        if ont.pon in pons_cto:
            score += W_PON_CTO
            motivos.append(f"mesma PON das âncoras da CTO (+{W_PON_CTO:g})")
        else:
            apoio = sum(perfil.pons.values())
            pena = PENALTY_PON if apoio >= 2 else PENALTY_PON_FRACA
            score += pena
            motivos.append(f"PON diferente das âncoras da CTO ({', '.join(sorted(pons_cto))}, "
                           f"{apoio} âncora(s)) ({pena:g})")
    elif pons_ramal:
        if ont.pon in pons_ramal:
            score += W_PON_RAMAL
            motivos.append(f"PON do {cto.ramal} (+{W_PON_RAMAL:g})")
        else:
            score += PENALTY_PON_RAMAL
            motivos.append(f"PON diferente do {cto.ramal} ({PENALTY_PON_RAMAL:g})")

    mediana = perfil.distancia_mediana if perfil else None
    if mediana is not None and ont.distance_km is not None:
        diff = abs(ont.distance_km - mediana)
        if diff > DIST_FAR_KM:
            score += PENALTY_DIST
            motivos.append(f"distância {ont.distance_km:.1f} km longe da faixa da CTO (~{mediana:.1f}) ({PENALTY_DIST:g})")
        else:
            pts = max(0.0, W_DIST_MAX - (diff / DIST_STEP_KM) * 0.5)
            if pts:
                score += pts
                motivos.append(f"distância {ont.distance_km:.1f} km ~ CTO {mediana:.1f} km (+{pts:g})")

    if None not in (ont.lat, ont.lon, cto.latitude, cto.longitude):
        metros = haversine_m(ont.lat, ont.lon, cto.latitude, cto.longitude)
        if metros <= 100:
            score += 2.0
            motivos.append(f"cliente a {metros:.0f} m da CTO (+2)")
        elif metros <= 250:
            score += 1.0
            motivos.append(f"cliente a {metros:.0f} m da CTO (+1)")
        elif metros > GEO_FAR_M:
            score += PENALTY_GEO_FAR
            motivos.append(f"cliente a {metros:.0f} m da CTO ({PENALTY_GEO_FAR:g})")

    n = cofalhas_ont.get(cto.pk, 0)
    if n:
        pts = min(W_COFALHA_MAX, n * W_COFALHA_POR_QUEDA)
        score += pts
        motivos.append(f"caiu junto com clientes da CTO {n}x (+{pts:g})")

    return score, motivos


def candidatas(ont, ctos, perfis, pons_por_ramal):
    """CTOs que fazem sentido avaliar para a ONT (evita pontuar as ~1000)."""
    escolhidas = {}
    for cto in ctos:
        perfil = perfis.get(cto.pk)
        if perfil and ont.pon in perfil.pons:
            escolhidas[cto.pk] = cto
        elif not perfil and ont.pon in pons_por_ramal.get((cto.olt_id, cto.ramal), set()):
            escolhidas[cto.pk] = cto
        elif None not in (ont.lat, ont.lon, cto.latitude, cto.longitude) and \
                haversine_m(ont.lat, ont.lon, cto.latitude, cto.longitude) <= GEO_CANDIDATE_M:
            escolhidas[cto.pk] = cto
    if ont.cto_cadastro is not None:
        escolhidas[ont.cto_cadastro.pk] = ont.cto_cadastro
    return list(escolhidas.values())


def evidencia(item, ont):
    """Score sem o bônus do cadastro - só o que a rede mostra."""
    score, cto, _ = item
    if ont.cto_cadastro is not None and cto.pk == ont.cto_cadastro.pk:
        return score - W_CADASTRO
    return score


def classificar(ont, ranking):
    """ranking: [(score, cto, motivos)] ordenado desc -> (status, ranking).
    No divergente o ranking volta reordenado só pela evidência da rede, para a
    CTO provável ser a que a rede aponta e não a do cadastro."""
    if not ranking:
        return 'sem_candidata', ranking

    if ont.cto_cadastro is not None:
        por_evidencia = sorted(ranking, key=lambda item: evidencia(item, ont), reverse=True)
        cadastro = next(item for item in ranking if item[1].pk == ont.cto_cadastro.pk)
        melhor = por_evidencia[0]
        # Divergente exige algo concreto CONTRA a CTO do cadastro (PON, distância
        # ou geografia negativas) - só faltar evidência a favor não basta.
        contra_cadastro = any('(-' in motivo for motivo in cadastro[2])
        if contra_cadastro and melhor[1].pk != ont.cto_cadastro.pk and \
                evidencia(melhor, ont) - evidencia(cadastro, ont) >= DIVERGENTE_MARGEM:
            return 'divergente', por_evidencia
        if ranking[0][1].pk == ont.cto_cadastro.pk and ranking[0][0] >= CONFIRMADO_MIN:
            return 'confirmado', ranking
        return 'incerto', ranking

    melhor_score = ranking[0][0]
    margem = melhor_score - ranking[1][0] if len(ranking) > 1 else melhor_score
    if melhor_score >= PROVAVEL_MIN and margem >= PROVAVEL_MARGEM:
        return 'provavel', ranking
    return 'incerto', ranking


def infer(onts, ctos, eventos=()):
    """Núcleo puro. onts: [Ont]; ctos: objetos Cto (pk, olt_id, ramal,
    latitude, longitude); eventos: [(pon, position, datetime)] de quedas.
    Devolve [(ont, status, ranking)], ranking = [(score, cto, motivos)] desc."""
    perfis, pons_por_ramal = aprender_perfis(onts)

    onts_por_pon = Counter(o.pon for o in onts)
    ancoras_por_posicao = {(o.pon, o.position): o.cto_cadastro.pk for o in onts if o.cto_cadastro is not None}
    quedas = detectar_quedas(eventos, onts_por_pon)
    cofalhas = contar_cofalhas(quedas, ancoras_por_posicao)

    resultado = []
    for ont in onts:
        ranking = []
        for cto in candidatas(ont, ctos, perfis, pons_por_ramal):
            perfil = perfis.get(cto.pk)
            if perfil is not None and ont.cto_cadastro is not None and cto.pk == ont.cto_cadastro.pk:
                perfil = perfil.sem(ont)
            score, motivos = pontuar(ont, cto, perfil,
                                     pons_por_ramal.get((cto.olt_id, cto.ramal), set()) if cto.ramal else set(),
                                     cofalhas.get((ont.pon, ont.position), {}))
            ranking.append((score, cto, motivos))
        ranking.sort(key=lambda x: x[0], reverse=True)
        status, ranking = classificar(ont, ranking)
        resultado.append((ont, status, ranking))
    return resultado, perfis, pons_por_ramal, quedas


def motivo_principal_contra(motivos):
    """Classifica por que uma CTO perdeu pontos (para o resumo dos divergentes)."""
    texto = ' '.join(motivos)
    if 'PON diferente' in texto:
        return 'PON diferente da CTO do cadastro'
    if 'longe da faixa' in texto:
        return 'distância óptica fora da faixa da CTO do cadastro'
    if 'cliente a' in texto and '(-' in texto:
        return 'cliente longe (geografia) da CTO do cadastro'
    return 'outra CTO com evidência mais forte'


def run_inference(olt, dias_eventos=30):
    """Carrega do banco, roda a inferência para uma OLT e grava CtoInferencia."""
    from datetime import timedelta

    from django.db import transaction
    from django.utils import timezone

    from olt.models import ONU, ClienteFibraIxc, Cto, CtoInferencia, OntEvent
    from olt.utils import parse_float

    clientes = {c.mac: c for c in ClienteFibraIxc.objects.filter(is_active=True)}
    ctos_por_ixc = {c.ixc_id: c for c in Cto.objects.filter(is_active=True).exclude(ixc_id=None)}

    onts = []
    for onu in ONU.objects.filter(olt=olt):
        cliente = clientes.get(onu.serial)
        cto_cad = ctos_por_ixc.get(cliente.id_caixa_ftth) if cliente and cliente.id_caixa_ftth else None
        onts.append(Ont(
            pon=onu.pon, position=onu.position, serial=onu.serial,
            distance_km=parse_float(onu.ont_olt),
            cliente_nome=cliente.nome if cliente else '',
            cto_cadastro=cto_cad,
            lat=parse_float(cliente.latitude) if cliente else None,
            lon=parse_float(cliente.longitude) if cliente else None,
        ))
    # lat/long 0 no IXC = vazio
    for o in onts:
        if o.lat == 0 or o.lon == 0:
            o.lat = o.lon = None

    # CTOs da OLT (KMZ) + as do IXC sem OLT definida (Ouro Fino, sem KMZ nomeado):
    # estas só viram candidatas por âncora ou geografia.
    ctos = list(Cto.objects.filter(is_active=True).filter(olt=olt)) + \
        list(Cto.objects.filter(is_active=True, olt__isnull=True))

    desde = timezone.now() - timedelta(days=dias_eventos)
    # Só desconexões (LOS / ONT inativa): RDI e alarmes de nível oscilam o tempo
    # todo e não indicam fibra em comum - contaminavam o agrupamento.
    eventos = [(e.pon, e.position, e.occurred_at) for e in
               OntEvent.objects.filter(olt=olt, is_clear=False, occurred_at__gte=desde,
                                       event_type__in=OntEvent.TYPES_QUEDA)
               .only('pon', 'position', 'occurred_at')]

    resultado, perfis, pons_por_ramal, quedas = infer(onts, ctos, eventos)

    agora = timezone.now()
    linhas = []
    motivos_divergencia = Counter()
    for ont, status, ranking in resultado:
        melhor = ranking[0] if ranking else (None, None, [])
        segundo = ranking[1] if len(ranking) > 1 else (None, None, [])
        cadastro = next((item for item in ranking
                         if ont.cto_cadastro is not None and item[1].pk == ont.cto_cadastro.pk), None)
        if status == 'divergente' and cadastro:
            motivos_divergencia[motivo_principal_contra(cadastro[2])] += 1
        linhas.append(CtoInferencia(
            olt=olt, pon=ont.pon, position=ont.position, serial=ont.serial,
            cliente_nome=ont.cliente_nome[:255], distance_km=ont.distance_km,
            cto_cadastro=ont.cto_cadastro, cto_provavel=melhor[1], score=melhor[0],
            cto_alternativa=segundo[1], score_alternativa=segundo[0],
            status=status, calculado_em=agora,
            motivos={
                'provavel': melhor[2],
                'alternativa': segundo[2],
                # Por que a CTO do cadastro ficou atrás (vazio se ela é a provável).
                'cadastro': cadastro[2] if cadastro and cadastro is not melhor else [],
            },
        ))
    with transaction.atomic():
        CtoInferencia.objects.filter(olt=olt).delete()
        CtoInferencia.objects.bulk_create(linhas, batch_size=500)

    resumo = {
        'onts': len(onts),
        'ancoras': sum(1 for o in onts if o.cto_cadastro is not None),
        'eventos': len(eventos),
        'quedas_uteis': len(quedas),
        'status': dict(Counter(status for _, status, _ in resultado)),
        'divergencia_por_motivo': dict(motivos_divergencia),
        'ramais_com_pon': {f"{r}": sorted(p) for (_, r), p in sorted(pons_por_ramal.items(), key=lambda x: x[0][1]) if p},
    }
    logger.info(f"Inferência de CTO ({olt.name}): {resumo['status']}")
    return resumo
