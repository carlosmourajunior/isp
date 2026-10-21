"""
Testes da leitura do KMZ e do casamento com as CTOs do IXC. O KML abaixo
reproduz a estrutura real do projeto de Borda da Mata (pastas
"Ramais/Ramal NN", descrição "08/26 ... F.O.01 -> Splitter 1:8").
"""
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, TestCase

from olt.client_utils import update_ctos
from olt.kmz import iter_placemarks, match_ctos, normalize_name, parse_cto_placemark
from olt.models import Cto

KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Borda da mata</name>
<Folder><name>Ramais</name>
  <Placemark><name>CA_03</name><Point><coordinates>-46.17627,-22.28154,0</coordinates></Point></Placemark>
  <Folder><name>Ramal 05</name>
    <Placemark><name>CA_235 (ampliada)</name>
      <description>08/26  M.P. Inicial: 31% M.P. Final: 62%  --------------------  F.O.01 -&gt; Splitter 1:8</description>
      <Point><coordinates>-46.170124,-22.276223,0</coordinates></Point></Placemark>
    <Placemark><name>CA_03</name><Point><coordinates>-46.17172,-22.26709,0</coordinates></Point></Placemark>
    <Placemark><name>Caixa de Emenda</name><Point><coordinates>-46.1,-22.2,0</coordinates></Point></Placemark>
    <Placemark><name>Cabo.01</name><LineString><coordinates>-46.1,-22.2,0 -46.2,-22.3,0</coordinates></LineString></Placemark>
  </Folder>
</Folder>
<Folder><name>Postes</name>
  <Placemark><name>CA_999</name><Point><coordinates>-46.0,-22.0,0</coordinates></Point></Placemark>
</Folder>
</Document></kml>"""


def caixas():
    return [c for c in (parse_cto_placemark(p) for p in iter_placemarks(KML)) if c]


def ixc(descricao, lat, lon):
    return SimpleNamespace(descricao=descricao, latitude=lat, longitude=lon)


class KmzParseTests(SimpleTestCase):

    def test_extrai_so_caixas_com_ramal_portas_e_splitter(self):
        kmz = {c['name']: c for c in caixas()}
        self.assertEqual(set(kmz), {'CA_03', 'CA_235 (ampliada)'})  # emenda, cabo e poste ficam fora
        ca235 = kmz['CA_235 (ampliada)']
        self.assertEqual(ca235['ramal'], 'Ramal 05')
        self.assertEqual(ca235['portas'], 8)
        self.assertEqual(ca235['splitter'], '1:8')
        self.assertEqual(ca235['tipo'], 'CA')
        self.assertAlmostEqual(ca235['lat'], -22.276223)

    def test_normalizacao_mantem_numeros(self):
        self.assertEqual(normalize_name('CA_235 (ampliada 1/4)'), 'CA_235')
        self.assertNotEqual(normalize_name('CA_03'), normalize_name('CA_003'))


class MatchCtosTests(SimpleTestCase):

    def test_nome_igual_e_perto_casa_por_nome(self):
        [(k, cto, metodo, _)] = match_ctos([c for c in caixas() if c['ramal'] == 'Ramal 05' and c['name'].startswith('CA_235')],
                                           [ixc('CA_235', -22.27623, -46.17013)])
        self.assertEqual(metodo, 'nome')

    def test_nome_repetido_escolhe_a_caixa_mais_proxima(self):
        perto_ramal05 = ixc('CA_03', -22.26710, -46.17170)
        perto_raiz = ixc('CA_03', -22.28155, -46.17628)
        resultado = {k['folder']: cto for k, cto, _, _ in match_ctos(
            [c for c in caixas() if c['name'] == 'CA_03'], [perto_raiz, perto_ramal05])}
        self.assertIs(resultado['Borda da mata/Ramais/Ramal 05'], perto_ramal05)
        self.assertIs(resultado['Borda da mata/Ramais'], perto_raiz)

    def test_sem_nome_igual_casa_por_coordenada_proxima(self):
        ca235 = [c for c in caixas() if c['name'].startswith('CA_235')]
        [(_, cto, metodo, dist)] = match_ctos(ca235, [ixc('OUTRO_NOME', -22.27623, -46.17013)])
        self.assertEqual(metodo, 'coordenada')
        self.assertLess(dist, 40)

    def test_longe_e_sem_nome_nao_casa(self):
        ca235 = [c for c in caixas() if c['name'].startswith('CA_235')]
        [(_, cto, _, _)] = match_ctos(ca235, [ixc('CA_235', -22.0, -46.0)])
        self.assertIsNone(cto)


def _resposta(registros):
    resp = mock.Mock(status_code=200)
    resp.json.return_value = {'total': str(len(registros)), 'registros': registros}
    return resp


@mock.patch.dict('os.environ', {'IXC_HOST': 'ixc.exemplo.com.br', 'IXC_TOKEN': 'token-de-teste'})
class UpdateCtosTests(TestCase):

    @mock.patch('olt.client_utils.requests.post')
    def test_grava_ctos_do_ixc_e_preserva_dados_do_kmz(self, mock_post):
        Cto.objects.create(ixc_id='1', descricao='CA_008', ramal='Ramal 01', kmz_portas=8)
        Cto.objects.create(ixc_id='999', descricao='REMOVIDA')
        so_kmz = Cto.objects.create(ixc_id=None, origem=Cto.ORIGEM_KMZ, descricao='CTO MC-01')
        # Registro no formato real de rad_caixa_ftth
        mock_post.return_value = _resposta([
            {'id': '1', 'descricao': 'CA_008', 'latitude': '-22.276223109155', 'longitude': '-46.170124775404',
             'capacidade': '8', 'status': 'A', 'id_projeto': '1'},
            {'id': '2', 'descricao': 'CA_013', 'latitude': '', 'longitude': '', 'capacidade': '', 'status': 'A', 'id_projeto': '1'},
        ])

        self.assertEqual(update_ctos(), 2)

        ca008 = Cto.objects.get(ixc_id='1')
        self.assertAlmostEqual(ca008.latitude, -22.276223109155)
        self.assertEqual(ca008.capacidade, 8)
        self.assertEqual(ca008.ramal, 'Ramal 01')  # dado do KMZ não é apagado pelo sync
        ca013 = Cto.objects.get(ixc_id='2')
        self.assertIsNone(ca013.latitude)
        self.assertIsNone(ca013.capacidade)
        self.assertFalse(Cto.objects.get(ixc_id='999').is_active)
        so_kmz.refresh_from_db()
        self.assertTrue(so_kmz.is_active)  # caixa só do KMZ não é desativada pelo sync do IXC
