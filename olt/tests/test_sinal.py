"""Sinal óptico (olt/sinal.py + /api/sinal/): faixas, variação e palpite de causa comum."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from olt.models import ONU, ClienteFibraIxc, Cto, CtoInferencia, Olt, OntEvent, OntSnapshot
from olt.sinal import analisar_series, categoria_alarme, faixa


class FuncoesPurasTests(APITestCase):

    def test_faixa(self):
        self.assertEqual(faixa(None), 'sem_leitura')
        self.assertEqual(faixa(-20), 'bom')
        self.assertEqual(faixa(-27), 'alerta')
        self.assertEqual(faixa(-29), 'alerta')
        self.assertEqual(faixa(-29.1), 'critico')

    def test_categoria_alarme(self):
        self.assertEqual(categoria_alarme('Received optical signal too low'), 'sinal_baixo')
        self.assertEqual(categoria_alarme('Signal Degraded from ONT'), 'sinal_degradado')
        self.assertIsNone(categoria_alarme('Remote Defect Indication from ONT'))

    def test_variacao_usa_periodo_anterior_como_referencia(self):
        agora = timezone.now()
        series = {
            'piorou': [(agora, -22.0), (agora, -25.5)],
            'estavel': [(agora, -22.0), (agora, -22.4)],
            'oscilando': [(agora, -22.0), (agora, -26.0), (agora, -22.1)],
            'uma_leitura': [(agora, -30.0)],
        }
        r = analisar_series(series, {'piorou': [-21.0, -21.2, -21.0]}, 2.0)
        self.assertEqual(set(r), {'piorou', 'oscilando'})
        self.assertEqual(r['piorou']['referencia'], -21.0)
        self.assertEqual(r['piorou']['delta'], -4.5)
        self.assertTrue(r['piorou']['referencia_periodo_anterior'])
        self.assertEqual(r['oscilando']['tipo'], 'oscilando')


class SinalApiTests(APITestCase):

    def setUp(self):
        self.client.force_authenticate(User.objects.create_user('u', password='p'))
        self.olt = Olt.objects.create(name='OLT Borda', host='10.0.0.1', username='u', password='p')
        self.agora = timezone.now()
        self.cx_a = Cto.objects.create(ixc_id='1', descricao='CA_001', olt=self.olt, ramal='Ramal 01')
        self.cx_b = Cto.objects.create(ixc_id='2', descricao='CA_002', olt=self.olt, ramal='Ramal 01')
        self.cx_c = Cto.objects.create(ixc_id='3', descricao='CA_003', olt=self.olt, ramal='Ramal 02')

        def ont(pos, pon, cto, antes, depois):
            serial = f'S{pon[-1]}{pos}'
            ONU.objects.create(olt=self.olt, pon=pon, position=pos, mac='', serial=serial, oper_state='up',
                               desc1='', desc2='', olt_rx_sig=depois[-1])
            CtoInferencia.objects.create(olt=self.olt, pon=pon, position=pos, serial=serial, status='provavel',
                                         cto_provavel=cto, calculado_em=self.agora, motivos={})
            for i, v in enumerate(antes):
                OntSnapshot.objects.create(olt=self.olt, taken_at=self.agora - timedelta(hours=40 - i), pon=pon,
                                           position=pos, serial=serial, olt_rx_sig=v)
            for i, v in enumerate(depois):
                OntSnapshot.objects.create(olt=self.olt, taken_at=self.agora - timedelta(hours=10 - i), pon=pon,
                                           position=pos, serial=serial, olt_rx_sig=v)
            return serial

        # PON 1/1/1/1: a caixa A inteira piora (3 de 3); B tem 1 de 3 piorando.
        for pos in (1, 2, 3):
            ont(pos, '1/1/1/1', self.cx_a, [-20, -20], [-20, -24])
        ont(4, '1/1/1/1', self.cx_b, [-21, -21], [-21, -25])
        for pos in (5, 6):
            ont(pos, '1/1/1/1', self.cx_b, [-21, -21], [-21, -21])
        # PON 1/1/1/2: um cliente isolado piora; o resto estável.
        self.isolado = ont(1, '1/1/1/2', self.cx_c, [-19, -19], [-19, -30])
        for pos in (2, 3, 4):
            ont(pos, '1/1/1/2', self.cx_c, [-19, -19], [-19, -19])
        ClienteFibraIxc.objects.create(mac=self.isolado, nome='Bia', login='bia@fibra')
        OntEvent.objects.create(olt=self.olt, occurred_at=self.agora - timedelta(hours=2), pon='1/1/1/2',
                                position=1, event_type='other', alarm_type='Received optical signal too low')

    def test_resumo(self):
        r = self.client.get('/api/sinal/resumo/').json()
        self.assertEqual(r['total'], 10)
        self.assertEqual(r['critico'], 1)
        self.assertEqual(r['bom'], 9)

    def test_variacao_agrupa_por_caixa_e_marca_individual(self):
        r = self.client.get('/api/sinal/variacao/?periodo=24h').json()
        self.assertEqual(r['contagem'], {'piorou': 5})
        caixas = [g for g in r['grupos'] if g['nivel'] == 'cto']
        self.assertEqual([(g['referencia'], g['afetados'], g['total']) for g in caixas], [('CA_001', 3, 3)])
        isolado = next(i for i in r['itens'] if i['serial'] == self.isolado)
        self.assertEqual(isolado['cliente_nome'], 'Bia')
        self.assertEqual(isolado['alarmes'], {'sinal_baixo': 1})
        self.assertTrue(isolado['diagnostico'].startswith('Individual'))
        self.assertEqual(isolado['delta'], -11.0)

    def test_variacao_mesma_pon_varias_caixas(self):
        # A caixa B piora inteira também -> 6 de 6 na PON, em 2 caixas: problema antes das caixas.
        for pos in (5, 6):
            OntSnapshot.objects.create(olt=self.olt, taken_at=self.agora - timedelta(hours=1), pon='1/1/1/1',
                                       position=pos, serial=f'S1{pos}', olt_rx_sig=-25)
        r = self.client.get('/api/sinal/variacao/').json()
        pon = [g for g in r['grupos'] if g['nivel'] == 'pon']
        self.assertEqual(len(pon), 1)
        self.assertEqual((pon[0]['pon'], pon[0]['afetados']), ('1/1/1/1', 6))
        self.assertEqual(r['grupos'][0]['nivel'], 'pon')

    def test_filtro_olt_e_periodo_invalido(self):
        outra = Olt.objects.create(name='OLT OF', host='10.0.0.2', username='u', password='p')
        r = self.client.get(f'/api/sinal/variacao/?olt={outra.id}&periodo=xx&limiar=abc').json()
        self.assertEqual((r['periodo'], r['limiar_db'], r['itens']), ('24h', 2.0, []))
