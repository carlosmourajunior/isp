"""Topologia do KMZ (olt/kmz_topologia.py): CTO -> splitter de distribuição."""
from django.test import SimpleTestCase

from olt.kmz import iter_placemarks, parse_cto_placemark
from olt.kmz_topologia import chave, parse_cd, parse_cto_texto, topologia

CD = """F.O.02 do CFOA_02 -> Splitter 1:2<br>Saída.01 -> Splitter 1:8<br>\tSaída.01 -> F.O.01 do Cabo.01<br>
\tSaída.02 -> F.O.02 do Cabo.01<br>Saída.02-> Splitter 1:8<br>\tSaída.01 -> F.O.03 do Cabo.01<br>"""


def kml(placemarks):
    return ('<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>X</name>'
            '<Folder><name>Ramais</name><Folder><name>Ramal 01</name>' + ''.join(placemarks) +
            '</Folder></Folder><Folder><name>CEO</name>'
            '<Placemark><name>301</name><Point><coordinates>-46.3000,-22.3000,0</coordinates></Point></Placemark>'
            '</Folder><Folder><name>DIST</name>'
            '<Placemark><name></name><LineString><coordinates>-46.3000,-22.3000,0 -46.3010,-22.3000,0'
            '</coordinates></LineString></Placemark>'
            '<Placemark><name></name><LineString><coordinates>-46.3010,-22.3000,0 -46.3020,-22.3000,0'
            '</coordinates></LineString></Placemark>'
            '</Folder><Folder><name>CTO</name>'
            '<Placemark><name>Marcador sem título</name><Point><coordinates>-46.3020,-22.3001,0</coordinates></Point></Placemark>'
            '</Folder></Document></kml>').encode()


def ponto(nome, desc, lon, lat):
    return (f'<Placemark><name>{nome}</name><description><![CDATA[{desc}]]></description>'
            f'<Point><coordinates>{lon},{lat},0</coordinates></Point></Placemark>')


def linha(nome, *coords):
    return (f'<Placemark><name>{nome}</name><LineString><coordinates>'
            + ' '.join(f'{lon},{lat},0' for lon, lat in coords) + '</coordinates></LineString></Placemark>')


class TopologiaTests(SimpleTestCase):

    def test_parse_cd(self):
        cd = parse_cd(CD)
        self.assertEqual(cd['entrada'], 'F.O.02 do CFOA_02')
        self.assertEqual(cd['saidas'][('CABO.01', 2)], (1, 2))
        self.assertEqual(cd['saidas'][('CABO.01', 3)], (2, 1))

    def test_parse_cto_com_fusao(self):
        fibra, fusoes = parse_cto_texto('08/20<br>F.O.02 -> Splitter 1:8<br>---<br>Constituição do Cabo.07<br>'
                                        'F.O.03 do Cabo.01 -> F.O.01 do Cabo.07')
        self.assertEqual((fibra, fusoes), (2, {'CABO.07': [(1, 'CABO.01', 3)]}))

    def test_texto_e_geometria(self):
        b = kml([
            ponto('CD_01', CD, -46.1000, -22.1000),
            linha('Cabo.01', (-46.1000, -22.1000), (-46.1010, -22.1000), (-46.1020, -22.1000)),
            ponto('CA_001', '08/10<br>F.O.01 -> Splitter 1:8', -46.1010, -22.1000),
            ponto('CA_002', '08/10<br>F.O.03 -> Splitter 1:8<br>Constituição do Cabo.02<br>'
                            'F.O.02 do Cabo.01 -> F.O.01 do Cabo.02', -46.1020, -22.1000),
            linha('Cabo.02', (-46.1020, -22.1000), (-46.1030, -22.1000)),
            ponto('CA_003', '08/10<br>F.O.01 -> Splitter 1:8', -46.1030, -22.1000),
        ])
        ctos = [c for c in (parse_cto_placemark(p) for p in iter_placemarks(b)) if c]
        t = topologia(b, ctos)
        por_nome = {c['name']: t.get(chave(c)) for c in ctos}
        self.assertEqual(por_nome['CA_001']['ceo'], 'CD_01 · 1:8 nº1')
        self.assertEqual((por_nome['CA_002']['ceo'], por_nome['CA_002']['ceo_saida']), ('CD_01 · 1:8 nº2', 1))
        self.assertEqual(por_nome['CA_003']['ceo'], 'CD_01 · 1:8 nº1')       # pela fusão: Cabo.02 F.O.01 <- Cabo.01 F.O.02
        self.assertEqual(por_nome['CA_003']['cabo'], 'Cabo.02 (fusão em CA_002)')
        self.assertEqual(por_nome['CA_003']['alimentacao'], 'F.O.02 do CFOA_02')
        sem_nome = por_nome['']
        self.assertEqual((sem_nome['ceo'], sem_nome['metodo']), ('CEO 301', 'geometria'))
