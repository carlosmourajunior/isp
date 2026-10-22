"""
Leitura do projeto da rede (KMZ/KML) e casamento das caixas com o cadastro
de CTOs do IXC.

Formatos conhecidos:
- Borda da Mata: caixas nomeadas (CA_235, CTO MC-01, CD_...) em pastas
  "Ramais/Ramal NN", descrição "08/26  M.P. Inicial: 31% ...  F.O.01 -> Splitter 1:8"
  (08 = portas). O IXC importa desse mesmo KMZ, então os nomes batem.
- Ouro Fino: caixas SEM nome ("Marcador sem título") na pasta "CTO" - casam
  com o IXC só por coordenada.
- Inconfidentes: "CTO-01-03" na pasta "Caixas de Terminação"; os "CD-xx" ficam em
  "Caixas de Emenda" (emenda, não atendimento).
"""
import math
import re
import zipfile
import xml.etree.ElementTree as ET

CTO_NAME_RE = re.compile(r'^\s*(CA|CTO|CD)\b|^\s*(CA|CTO|CD)[_\-\s]', re.IGNORECASE)
RAMAL_RE = re.compile(r'Ramal\s*(\d+)', re.IGNORECASE)
# Pastas cujos pontos são caixas de atendimento mesmo sem nome reconhecível.
PASTA_CAIXAS_RE = re.compile(r'^(CTOS?|CAIXAS? DE (TERMINA|ATENDIMENTO).*)$', re.IGNORECASE)
# O Google Earth dá esses nomes a marcadores criados sem nome.
NOMES_VAZIOS = {'', 'MARCADOR SEM TÍTULO', 'MARCADOR DE LOCAL SEM TÍTULO', 'UNTITLED PLACEMARK'}
DESCARTAR_RE = re.compile(r'EMENDA|POSTE|RESERVA', re.IGNORECASE)
PORTAS_RE = re.compile(r'^\s*(\d{1,3})\s*/\s*(\d{1,4})')
SPLITTER_RE = re.compile(r'Splitter\s*(1:\d+)', re.IGNORECASE)

# Distâncias de casamento (metros).
NAME_MATCH_MAX_M = 150      # nomes se repetem no KMZ (há 4 "CA_03"): mesmo nome só vale se perto
COORD_MATCH_MAX_M = 40      # sem nome igual: aceita a caixa do IXC mais próxima até aqui


def _tag(el):
    return el.tag.split('}')[-1]


def _child_text(el, name):
    for child in el:
        if _tag(child) == name:
            return (child.text or '').strip()
    return ''


def read_kml_bytes(path):
    """Aceita .kmz (zip com doc.kml) ou .kml puro."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            kml_name = next((n for n in z.namelist() if n.lower().endswith('.kml')), None)
            if kml_name is None:
                raise ValueError(f"{path}: KMZ sem arquivo .kml dentro")
            return z.read(kml_name)
    with open(path, 'rb') as f:
        return f.read()


def iter_placemarks(kml_bytes):
    """-> dicts {name, folder, description, lat, lon} só de Placemarks com Point."""
    root = ET.fromstring(kml_bytes)

    def walk(el, folders):
        tag = _tag(el)
        if tag in ('Folder', 'Document'):
            folders = folders + [_child_text(el, 'name')]
        if tag == 'Placemark':
            coords = None
            for sub in el.iter():
                if _tag(sub) == 'Point':
                    for c in sub.iter():
                        if _tag(c) == 'coordinates' and c.text:
                            coords = c.text.strip().split()[0]
            if coords:
                parts = coords.split(',')
                yield {
                    'name': _child_text(el, 'name'),
                    'folder': '/'.join(f for f in folders if f),
                    'description': _child_text(el, 'description'),
                    'lon': float(parts[0]),
                    'lat': float(parts[1]),
                }
            return
        for child in el:
            yield from walk(child, folders)

    yield from walk(root, [])


def normalize_name(name):
    """'CA_235 (ampliada 1/4)' -> 'CA_235'. Não mexe nos números: no KMZ,
    'CA_03' e 'CA_003' são caixas diferentes, e o IXC importa os nomes
    exatamente como estão no KMZ."""
    name = re.sub(r'\(.*?\)', '', name or '').upper()
    return re.sub(r'\s+', '', name).replace('-', '_')


def cto_tipo(name):
    """'CA_235' -> 'CA', 'CTO MC-01' -> 'CTO', 'CD_05' / 'CD-PONTILHÃO' -> 'CD'."""
    match = re.match(r'\s*(CA|CTO|CD)', name or '', re.IGNORECASE)
    return match.group(1).upper() if match else ''


def nome_vazio(name):
    return (name or '').strip().upper() in NOMES_VAZIOS


def parse_cto_placemark(pm):
    """Placemark de caixa -> dados do KMZ, ou None se não for caixa.

    É caixa se o nome começa com CA/CTO/CD ou se está numa pasta de caixas
    (ex.: "CTO", "Caixas de Terminação") - mesmo sem nome.
    """
    pasta = pm['folder'].split('/')[-1].strip() if pm['folder'] else ''
    pela_pasta = bool(PASTA_CAIXAS_RE.match(pasta))
    if not CTO_NAME_RE.match(pm['name'] or '') and not pela_pasta:
        return None
    # Emendas, postes e reservas técnicas não são caixas de atendimento.
    if DESCARTAR_RE.search(pm['name'] or '') or DESCARTAR_RE.search(pm['folder']):
        return None
    if nome_vazio(pm['name']):
        pm = {**pm, 'name': ''}
    ramal = RAMAL_RE.search(pm['folder'])
    portas = PORTAS_RE.match(pm['description'])
    splitter = SPLITTER_RE.search(pm['description'])
    return {
        **pm,
        'tipo': cto_tipo(pm['name']) or 'CTO',
        'ramal': f"Ramal {int(ramal.group(1)):02d}" if ramal else '',
        'portas': int(portas.group(1)) if portas else None,
        'splitter': splitter.group(1) if splitter else '',
    }


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def match_ctos(kmz_ctos, ixc_ctos):
    """Casa caixas do KMZ com caixas do IXC.

    kmz_ctos: saída de parse_cto_placemark. ixc_ctos: objetos com
    .descricao, .latitude, .longitude. Devolve [(kmz, ixc_ou_None, metodo, distancia_m)].
    Nome primeiro (conferindo distância, porque nomes se repetem entre
    cidades); senão a caixa do IXC mais próxima, até COORD_MATCH_MAX_M.
    """
    by_name = {}
    with_coords = []
    for cto in ixc_ctos:
        by_name.setdefault(normalize_name(cto.descricao), []).append(cto)
        if cto.latitude is not None and cto.longitude is not None:
            with_coords.append(cto)

    def dist(k, c):
        if c.latitude is None or c.longitude is None:
            return None
        return haversine_m(k['lat'], k['lon'], c.latitude, c.longitude)

    result = []
    for k in kmz_ctos:
        # Caixa sem nome no KMZ: só a coordenada serve.
        candidates = by_name.get(normalize_name(k['name']), []) if k['name'] else []
        best = None
        for c in candidates:
            d = dist(k, c)
            if d is None or d <= NAME_MATCH_MAX_M:
                if best is None or (d or 0) < (best[1] or 0):
                    best = (c, d)
        if best:
            result.append((k, best[0], 'nome', best[1]))
            continue

        nearest = min(((c, dist(k, c)) for c in with_coords), key=lambda x: x[1], default=None)
        if nearest and nearest[1] <= COORD_MATCH_MAX_M:
            result.append((k, nearest[0], 'coordenada', nearest[1]))
        else:
            result.append((k, None, '', None))
    return result


def nome_para_exibir(kmz):
    """Caixa sem nome no KMZ e sem par no IXC precisa de algum nome na tela."""
    return kmz['name'] or f"Sem nome ({kmz['lat']:.5f}, {kmz['lon']:.5f})"
