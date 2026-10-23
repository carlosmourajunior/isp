"""Análise de caixas com sinal ruim (olt/sinal_caixas.py)."""
from django.contrib.auth.models import User
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from olt.models import ONU, Cto, CtoInferencia, Olt
from olt.sinal_caixas import analisar, perda_splitter

N = 0


def ont(pon, sinal, cto=None, dist=2.0, serial=None):
    global N
    N += 1
    return {'serial': serial or f'S{N}', 'cliente': f'C{N}', 'olt_id': 1, 'olt_nome': 'OLT', 'pon': pon,
            'sinal': sinal, 'ont_rx': None, 'distancia': dist, 'cto': cto}


def cx(i, ramal='Ramal 01', splitter='1:8', extras=None, ceo='', cabo='', alimentacao=''):
    return {'id': i, 'descricao': f'CA_{i:03d}', 'ramal': ramal, 'splitter': splitter, 'portas': 8,
            'extras': extras or [], 'ceo': ceo, 'cabo': cabo, 'alimentacao': alimentacao}


class AnaliseTests(SimpleTestCase):

    def niveis(self, achados):
        return [(a['nivel'], a['referencia'], a['severidade']) for a in achados]

    def test_perda_splitter(self):
        self.assertEqual(perda_splitter('1:8'), 10.0)
        self.assertEqual(perda_splitter('1:16'), 13.0)
        self.assertIsNone(perda_splitter(''))

    def test_caixa_toda_baixa_com_vizinhas_boas(self):
        a, b, c = cx(1), cx(2), cx(3)
        onts = [ont('P', s, a) for s in (-27.5, -27.8, -28.0)] + \
               [ont('P', s, b) for s in (-22.0, -22.5, -23.0)] + [ont('P', s, c) for s in (-21.5, -22.0)]
        achados = analisar(onts, -26)
        self.assertEqual(self.niveis(achados), [('cto', 'CA_001', 'alta')])
        self.assertIn('splitter da CTO', achados[0]['diagnostico'])

    def test_splitter_maior_explica_a_diferenca(self):
        a = cx(1, splitter='1:16')
        onts = [ont('P', s, a) for s in (-26.2, -26.5, -26.8)] + \
               [ont('P', s, cx(2)) for s in (-23.5, -23.8, -24.0)] + [ont('P', s, cx(3)) for s in (-23.5, -24.0)]
        achados = analisar(onts, -26)
        self.assertEqual(achados[0]['severidade'], 'baixa')
        self.assertEqual(achados[0]['esperado_splitter'], 3.0)

    def test_pon_inteira_baixa(self):
        onts = [ont('P', s, cx(i)) for i, s in enumerate((-27, -27.5, -28, -26.5, -27.2), start=1)]
        self.assertEqual(self.niveis(analisar(onts, -26))[0], ('pon', 'PON P', 'alta'))

    def test_ramal_baixo(self):
        r2 = [ont('P', s, cx(i, ramal='Ramal 02')) for i, s in ((5, -27.5), (5, -27.8), (6, -28.0), (6, -27.6))]
        r1 = [ont('P', s, cx(i)) for i, s in ((1, -21), (1, -21.5), (2, -22), (2, -21.8), (3, -22.2), (3, -21.4))]
        achados = analisar(r1 + r2, -26)
        self.assertEqual(self.niveis(achados), [('ramal', 'Ramal 02 (PON P)', 'alta')])

    def test_cliente_isolado(self):
        a = cx(1)
        onts = [ont('P', -29.5, a), ont('P', -22.0, a), ont('P', -22.4, a)] + [ont('P', -22, cx(2)) for _ in range(3)]
        achados = analisar(onts, -26)
        self.assertEqual(self.niveis(achados), [('clientes', 'CA_001', 'baixa')])
        self.assertIn('drop', achados[0]['diagnostico'])

    def test_splitter_em_cascata(self):
        a = cx(1, extras=[8])
        onts = [ont('P', s, a) for s in (-30, -30.5, -22, -22.2, -22.5)] + [ont('P', -22, cx(2)) for _ in range(3)]
        self.assertIn('splitter adicionado', analisar(onts, -26)[0]['diagnostico'])

    def test_tendencia(self):
        onts = [ont('P', s, cx(1), serial=f'T{i}') for i, s in enumerate((-27.5, -27.8, -28.0))] + \
               [ont('P', -22, cx(2)) for _ in range(3)]
        historico = {'T0': -23.0, 'T1': -23.2, 'T2': -23.1}
        t = analisar(onts, -26, historico)[0]['tendencia']
        self.assertLess(t['variacao'], -4)
        self.assertIn('recente', t['texto'])


class TopologiaNaAnaliseTests(SimpleTestCase):

    def test_metade_da_pon_ruim_culpa_a_ceo(self):
        lado1 = [ont('P', s, cx(i, ceo='CD_01 · 1:8 nº1')) for i, s in ((1, -27.5), (1, -27.9), (2, -28.0), (3, -27.4))]
        lado2 = [ont('P', s, cx(i, ceo='CD_01 · 1:8 nº2')) for i, s in ((4, -22.0), (5, -22.3), (6, -21.8), (6, -22.1))]
        achados = analisar(lado1 + lado2, -26)
        self.assertEqual([(a['nivel'], a['ceo']) for a in achados], [('ceo', 'CD_01 · 1:8 nº1')])
        self.assertIn('1:2 que o alimenta', achados[0]['diagnostico'])

    def test_cabo_depois_da_fusao(self):
        ceo = 'CD_01 · 1:8 nº1'
        ruim = [ont('P', s, cx(i, ceo=ceo, cabo='Cabo.07 (fusão em CA_013)')) for i, s in ((1, -27.5), (2, -27.9), (2, -28))]
        bom = [ont('P', s, cx(i, ceo=ceo, cabo='Cabo.01')) for i, s in ((3, -22), (4, -22.3), (5, -21.8))]
        outra = [ont('P', -22, cx(9, ceo='CD_01 · 1:8 nº2')) for _ in range(3)]
        achados = analisar(ruim + bom + outra, -26)
        self.assertEqual([a['nivel'] for a in achados], ['cabo'])
        self.assertIn('fusão', achados[0]['diagnostico'])

    def test_pon_toda_e_backbone(self):
        onts = []
        for pon, base in (('P1', 1), ('P2', 10)):
            for i in range(4):
                onts.append(ont(pon, -27.5 - i * 0.1, cx(base + i, ceo=f'CD_{pon} · 1:8 nº{1 + i % 2}',
                                                         alimentacao=f'F.O.0{i % 2 + 1} do CFOA_02')))
        achados = analisar(onts, -26)
        self.assertEqual(achados[0]['nivel'], 'backbone')
        self.assertIn('CFOA_02', achados[0]['referencia'])
        self.assertIn('splitter 1:2', next(a for a in achados if a['nivel'] == 'pon')['diagnostico'])


class SinalCaixasApiTests(APITestCase):

    def test_endpoint(self):
        self.client.force_authenticate(User.objects.create_user('u', password='p'))
        olt = Olt.objects.create(name='OLT', host='10.0.0.1', username='u', password='p')
        cto = Cto.objects.create(ixc_id='1', descricao='CA_001', olt=olt, ramal='Ramal 01', kmz_splitter='1:8')
        agora = timezone.now()
        for pos, s in enumerate((-27.0, -27.4), start=1):
            ONU.objects.create(olt=olt, pon='1/1/1/1', position=pos, serial=f'S{pos}', mac='', oper_state='up',
                               desc1='', desc2='', olt_rx_sig=s, ont_olt='2.1')
            CtoInferencia.objects.create(olt=olt, pon='1/1/1/1', position=pos, serial=f'S{pos}', status='confirmado',
                                         cto_provavel=cto, calculado_em=agora, motivos={})
        ONU.objects.create(olt=olt, pon='1/1/1/1', position=9, serial='OFF', mac='', oper_state='down',
                           desc1='', desc2='', olt_rx_sig=None)
        r = self.client.get('/api/sinal/caixas/?limiar=-26').json()
        self.assertEqual((r['onts_analisadas'], r['onts_ruins']), (2, 2))
        self.assertEqual(r['achados'][0]['cto']['descricao'], 'CA_001')
        self.assertEqual(r['achados'][0]['severidade'], 'media')       # sem vizinhas para comparar
        self.assertNotIn('_ctos', r['achados'][0])
        m = self.client.get('/api/sinal/caixas/mapa/?limiar=-26').json()
        self.assertEqual(m['achados'][0]['ctos'], [cto.id])
        self.assertEqual(m['caixas'], [])                              # CTO sem coordenada não vai pro mapa
        cto.latitude, cto.longitude = -22.27, -46.17
        cto.save()
        m = self.client.get('/api/sinal/caixas/mapa/?limiar=-26').json()
        self.assertEqual((m['caixas'][0]['descricao'], m['caixas'][0]['ruins']), ('CA_001', 2))
