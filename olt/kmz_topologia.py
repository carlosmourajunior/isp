"""
Topologia do projeto (KMZ): de qual splitter de distribuição (CEO / CD) cada CTO sai.

Padrão da rede: PON -> 1:2 -> 1:8 (na CEO/CD) -> 1:8 (na CTO) = 128 clientes por PON.
Saber qual 1:8 de distribuição alimenta cada CTO permite culpar a CEO quando todas
as caixas atrás dela estão ruins e as do outro 1:8 da mesma PON estão boas.

Dois jeitos de descobrir, nesta ordem:

1. Texto (Borda da Mata): o CD de cada ramal descreve as saídas -
       F.O.02 do CFOA_02 -> Splitter 1:2
       Saída.01 -> Splitter 1:8
           Saída.01 -> F.O.01 do Cabo.01 ...
   e cada CTO diz a fibra dela ("F.O.02 -> Splitter 1:8") e as fusões feitas nela
   ("Constituição do Cabo.07: F.O.03 do Cabo.01 -> F.O.01 do Cabo.07"). O cabo em que
   a CTO está sai da geometria (cabo que passa pela caixa); a fibra é seguida pelas
   fusões até a saída do CD.
2. Geometria (Ouro Fino, CEOs só com número e cabos sem descrição): segue os cabos
   de distribuição a partir da CTO até chegar numa CEO.
"""
import html
import re
from collections import defaultdict, deque

from .kmz import _child_text, _tag, haversine_m

# Pastas de cabos que não são distribuição (cordoalha, postes, backbone, áreas).
PASTA_NAO_CABO_RE = re.compile(r'CORDOALHA|POSTE|ZONA|BACK|^REDE$|RESERVA', re.IGNORECASE)
CEO_NOME_RE = re.compile(r'^\s*(CD|CEO)\b|^\s*(CD|CEO)[_\-\s]', re.IGNORECASE)
CEO_PASTA_RE = re.compile(r'^(CEO|CEOS|CAIXAS? DE EMENDA)$', re.IGNORECASE)
TEM_SPLITTER_RE = re.compile(r'Split(t)?er|Splitagem', re.IGNORECASE)

CD_ENTRADA_RE = re.compile(r'F\.?O\.?\s*0*(\d+)\s+do\s+([\w.\-]+)\s*->\s*Splitter\s*(1:\d+)', re.IGNORECASE)
CD_RAMO_RE = re.compile(r'^\s*Sa[ií]da\.?\s*0*(\d+)\s*->\s*Splitter\s*(1:\d+)', re.IGNORECASE)
CD_SAIDA_RE = re.compile(r'^\s*Sa[ií]da\.?\s*0*(\d+)\s*->\s*F\.?O\.?\s*0*(\d+)\s+do\s+([\w.\-]+)', re.IGNORECASE)
CTO_FIBRA_RE = re.compile(r'F\.?O\.?\s*0*(\d+)\s*->\s*Splitter', re.IGNORECASE)
CONSTITUICAO_RE = re.compile(r'Constitui[cç][aã]o\s+do\s+([\w.\-]+)', re.IGNORECASE)
FUSAO_RE = re.compile(r'F\.?O\.?\s*0*(\d+)\s+do\s+([\w.\-]+)\s*->\s*F\.?O\.?\s*0*(\d+)\s+do\s+([\w.\-]+)', re.IGNORECASE)

PERTO_CABO_M = 40        # caixa "está" no cabo se algum vértice está até aqui (no texto a fibra ainda tem de bater)
PERTO_CABO_GEO_M = 35    # na geometria não há fibra para confirmar
LIGA_CABOS_M = 10        # ponta de um cabo encostada em outro = continuação
CEO_NA_PONTA_M = 20


def texto_limpo(descricao):
    t = re.sub(r'<br\s*/?>', '\n', descricao or '', flags=re.IGNORECASE)
    return html.unescape(re.sub(r'<[^>]+>', ' ', t))


def iter_elementos(kml_bytes):
    """-> (pontos, linhas): dicts {name, folder, description, coords[(lat, lon)]}."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(kml_bytes)
    pontos, linhas = [], []

    def walk(el, folders):
        tag = _tag(el)
        if tag in ('Folder', 'Document'):
            folders = folders + [_child_text(el, 'name')]
        if tag == 'Placemark':
            for sub in el.iter():
                if _tag(sub) in ('Point', 'LineString'):
                    for c in sub.iter():
                        if _tag(c) == 'coordinates' and c.text:
                            coords = []
                            for par in c.text.split():
                                p = par.split(',')
                                coords.append((float(p[1]), float(p[0])))
                            item = {'name': _child_text(el, 'name'), 'folder': '/'.join(f for f in folders if f),
                                    'description': _child_text(el, 'description'), 'coords': coords}
                            (pontos if _tag(sub) == 'Point' else linhas).append(item)
                            return
            return
        for child in el:
            walk(child, folders)

    walk(root, [])
    return pontos, linhas


def _pasta(item):
    return item['folder'].split('/')[-1].strip() if item['folder'] else ''


def _dist_ponto_linha(lat, lon, linha):
    return min(haversine_m(lat, lon, a, b) for a, b in linha['coords'])


# --------------------------------------------------------------------- texto (CD)
def parse_cd(descricao):
    """Descrição do CD -> {'entrada': 'F.O.02 do CFOA_02', 'cabo_entrada', 'primeiro': '1:2',
    'saidas': {(cabo, fo): (ramo, saida)}} ou None."""
    texto = texto_limpo(descricao)
    entrada = CD_ENTRADA_RE.search(texto)
    if not entrada:
        return None
    saidas, ramo = {}, None
    for linha in texto.splitlines():
        m = CD_RAMO_RE.match(linha)
        if m:
            ramo = int(m.group(1))
            continue
        m = CD_SAIDA_RE.match(linha)
        if m:
            saidas[(m.group(3).upper(), int(m.group(2)))] = (ramo or 1, int(m.group(1)))
    if not saidas:
        return None
    return {'entrada': f"F.O.{int(entrada.group(1)):02d} do {entrada.group(2)}", 'cabo_entrada': entrada.group(2),
            'primeiro': entrada.group(3), 'tem_ramos': ramo is not None, 'saidas': saidas}


def parse_cto_texto(descricao):
    """-> (fibra da CTO ou None, {cabo_saida: [(fo_saida, cabo_origem, fo_origem)]})."""
    texto = texto_limpo(descricao)
    fibra = CTO_FIBRA_RE.search(texto)
    fusoes = defaultdict(list)
    atual = None
    for linha in texto.splitlines():
        m = CONSTITUICAO_RE.search(linha)
        if m:
            atual = m.group(1).upper()
            continue
        m = FUSAO_RE.search(linha)
        if m and atual:
            fusoes[m.group(4).upper()].append((int(m.group(3)), m.group(2).upper(), int(m.group(1))))
    return (int(fibra.group(1)) if fibra else None), dict(fusoes)


def _por_texto(ctos, pontos, linhas):
    """Borda: CD + fusões. Trabalha por pasta (cada ramal tem o seu Cabo.01, Cabo.02...)."""
    resultado = {}
    por_pasta_pts, por_pasta_lns = defaultdict(list), defaultdict(list)
    for p in pontos:
        por_pasta_pts[p['folder']].append(p)
    for ln in linhas:
        por_pasta_lns[ln['folder']].append(ln)

    for pasta, pts in por_pasta_pts.items():
        cds = [(p, parse_cd(p['description'])) for p in pts if CEO_NOME_RE.match(p['name'] or '')]
        cds = [(p, cd) for p, cd in cds if cd]
        if not cds:
            continue
        # (cabo, fibra) -> (cabo, fibra) de origem, e onde foi a fusão.
        fusoes, local_fusao = {}, {}
        for p in pts:
            _, fs = parse_cto_texto(p['description'])
            for cabo_saida, lista in fs.items():
                for fo_s, cabo_o, fo_o in lista:
                    fusoes[(cabo_saida, fo_s)] = (cabo_o, fo_o)
                    local_fusao[cabo_saida] = p['name']
        cabos = [ln for ln in por_pasta_lns.get(pasta, []) if ln['name']]

        def origem(cabo, fo, passos=0):
            for cd_p, cd in cds:
                if (cabo, fo) in cd['saidas']:
                    return cd_p, cd, cd['saidas'][(cabo, fo)]
            if (cabo, fo) in fusoes and passos < 20:
                return origem(*fusoes[(cabo, fo)], passos + 1)
            return None

        for c in ctos:
            if c['folder'] != pasta or CEO_NOME_RE.match(c['name'] or ''):
                continue
            fibra, fs = parse_cto_texto(c['description'])
            if fibra is None:
                continue
            saem_daqui = set(fs)
            candidatos = sorted(((ln, _dist_ponto_linha(c['lat'], c['lon'], ln)) for ln in cabos
                                 if ln['name'].upper() not in saem_daqui), key=lambda x: x[1])
            for ln, d in candidatos:
                if d > PERTO_CABO_M:
                    break
                achado = origem(ln['name'].upper(), fibra)
                if achado:
                    cd_p, cd, (ramo, saida) = achado
                    cabo = ln['name']
                    resultado[_chave(c)] = {
                        'ceo': f"{cd_p['name']} · 1:8 nº{ramo}" if cd['tem_ramos'] else cd_p['name'],
                        'ceo_saida': saida,
                        'alimentacao': cd['entrada'],
                        'cabo': f"{cabo} (fusão em {local_fusao[cabo.upper()]})" if cabo.upper() in local_fusao else cabo,
                        'metodo': 'texto',
                    }
                    break
    return resultado


# ------------------------------------------------------------------ geometria
def _por_geometria(ctos, pontos, linhas, ja_resolvidas):
    ceos = [p for p in pontos
            if CEO_PASTA_RE.match(_pasta(p)) or CEO_NOME_RE.match(p['name'] or '')
            or TEM_SPLITTER_RE.search(p['name'] or '') and 'EMENDA' in (p['name'] or '').upper()]
    cabos = [ln for ln in linhas if not PASTA_NAO_CABO_RE.search(_pasta(ln)) and len(ln['coords']) >= 2]
    if not ceos or not cabos:
        return {}

    # Cabos encostados (ponta de um em qualquer vértice do outro) formam um grafo.
    vizinhos = defaultdict(set)
    for i, a in enumerate(cabos):
        for j, b in enumerate(cabos):
            if i < j and any(_dist_ponto_linha(lat, lon, b) <= LIGA_CABOS_M for lat, lon in (a['coords'][0], a['coords'][-1])) \
                    or i < j and any(_dist_ponto_linha(lat, lon, a) <= LIGA_CABOS_M for lat, lon in (b['coords'][0], b['coords'][-1])):
                vizinhos[i].add(j)
                vizinhos[j].add(i)
    ceo_do_cabo = {}
    for i, ln in enumerate(cabos):
        perto = [(haversine_m(lat, lon, *ceo['coords'][0]), ceo) for ceo in ceos for lat, lon in (ln['coords'][0], ln['coords'][-1])]
        perto = [x for x in perto if x[0] <= CEO_NA_PONTA_M]
        if perto:
            ceo_do_cabo[i] = min(perto, key=lambda x: x[0])[1]

    resultado = {}
    for c in ctos:
        if _chave(c) in ja_resolvidas or CEO_NOME_RE.match(c['name'] or '') or CEO_PASTA_RE.match(_pasta(c)):
            continue
        inicio = [i for i, ln in enumerate(cabos) if _dist_ponto_linha(c['lat'], c['lon'], ln) <= PERTO_CABO_GEO_M]
        visto, fila, achado = set(inicio), deque((i, 0) for i in inicio), None
        while fila:
            i, saltos = fila.popleft()
            if i in ceo_do_cabo:
                achado = (ceo_do_cabo[i], saltos)
                break
            for j in vizinhos[i]:
                if j not in visto and saltos < 30:
                    visto.add(j)
                    fila.append((j, saltos + 1))
        if achado:
            ceo = achado[0]
            nome = ceo['name'] or f"({ceo['coords'][0][0]:.5f}, {ceo['coords'][0][1]:.5f})"
            resultado[_chave(c)] = {'ceo': nome if CEO_NOME_RE.match(nome) else f"CEO {nome}", 'ceo_saida': None,
                                    'alimentacao': '', 'cabo': '', 'metodo': 'geometria'}
    return resultado


def _chave(c):
    return (c['name'], round(c['lat'], 6), round(c['lon'], 6))


def topologia(kml_bytes, ctos):
    """ctos: caixas já lidas por kmz.parse_cto_placemark. -> {chave(cto): {...}}."""
    pontos, linhas = iter_elementos(kml_bytes)
    por_texto = _por_texto(ctos, pontos, linhas)
    return {**_por_geometria(ctos, pontos, linhas, por_texto), **por_texto}


chave = _chave
