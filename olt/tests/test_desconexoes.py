"""Análise de desconexões (olt/desconexoes.py + /api/desconexoes/)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase

from olt.models import ONU, ClienteFibraIxc, Olt, OntEvent, OntSnapshot


class DesconexoesTests(APITestCase):

    def setUp(self):
        self.client.force_authenticate(User.objects.create_user('u', password='p'))
        self.olt = Olt.objects.create(name='OLT Borda', host='10.0.0.1', username='u', password='p')
        self.agora = timezone.now()

    def onu(self, serial, pos=1, oper='up', admin='up'):
        return ONU.objects.create(olt=self.olt, pon='1/1/1/1', position=pos, mac='', serial=serial,
                                  oper_state=oper, admin_state=admin, desc1='', desc2='')

    def cliente(self, serial, nome, contrato='A', internet='A', vinculado=True):
        return ClienteFibraIxc.objects.create(mac=serial, nome=nome, login=f'{serial}@x', is_active=True,
                                              status_contrato=contrato, status_internet=internet,
                                              vinculado=vinculado, id_contrato='1' if vinculado else '')

    def queda(self, serial, quando, tipo=OntEvent.TYPE_DYING_GASP, duracao_min=30):
        OntEvent.objects.create(olt=self.olt, occurred_at=quando, pon='1/1/1/1', position=1, serial=serial,
                                event_type=tipo, is_clear=False)
        OntEvent.objects.create(olt=self.olt, occurred_at=quando + timedelta(minutes=duracao_min), pon='1/1/1/1',
                                position=1, serial=serial, event_type=tipo, is_clear=True)

    def snapshot(self, serial, quando, oper):
        OntSnapshot.objects.create(olt=self.olt, taken_at=quando, pon='1/1/1/1', position=1, serial=serial,
                                   oper_state=oper)

    # ---- regra 1 ----
    def test_recorrentes_exige_dias_minimos_e_classifica(self):
        self.onu('DIARIO')
        self.onu('POUCO', pos=2)
        self.cliente('DIARIO', 'Cliente Diário')
        # cai às 23h (horário de Brasília = 02h UTC) por 12 dias seguidos
        base = self.agora.replace(hour=2, minute=0, second=0, microsecond=0)
        for d in range(1, 13):
            self.queda('DIARIO', base - timedelta(days=d))
        for d in (1, 2, 3):
            self.queda('POUCO', base - timedelta(days=d))

        r = self.client.get('/api/desconexoes/recorrentes/?janela=14&min_dias=10').json()
        self.assertEqual(r['total'], 1)
        item = r['itens'][0]
        self.assertEqual(item['serial'], 'DIARIO')
        self.assertEqual(item['cliente_nome'], 'Cliente Diário')
        self.assertEqual(item['dias_com_queda'], 12)
        self.assertEqual(item['causa'], 'energia')
        self.assertTrue(item['noturno'])
        self.assertEqual(item['hora_tipica'], 23)
        self.assertEqual(item['duracao_mediana_min'], 30.0)

    def test_recorrentes_ignora_eventos_other_e_quedas_fora_da_janela(self):
        self.onu('RUIDO')
        base = self.agora
        for d in range(1, 13):
            self.queda('RUIDO', base - timedelta(days=d), tipo=OntEvent.TYPE_OTHER)
        for d in range(20, 32):  # antigas demais
            self.queda('RUIDO', base - timedelta(days=d))
        r = self.client.get('/api/desconexoes/recorrentes/?janela=14&min_dias=3').json()
        self.assertEqual(r['total'], 0)

    def test_recorrentes_fibra_quando_inativa(self):
        self.onu('FIBRA')
        base = self.agora.replace(hour=15, minute=0, second=0, microsecond=0)
        for d in range(1, 6):
            self.queda('FIBRA', base - timedelta(days=d), tipo=OntEvent.TYPE_INATIVA)
        r = self.client.get('/api/desconexoes/recorrentes/?janela=7&min_dias=5').json()
        self.assertEqual(r['itens'][0]['causa'], 'fibra')
        self.assertFalse(r['itens'][0]['noturno'])

    # ---- regra 2 ----
    def test_offline_ativos_so_cliente_totalmente_ativo_e_ha_mais_de_5_dias(self):
        for serial, pos in (('ATIVO_8D', 1), ('ATIVO_2D', 2), ('BLOQUEADO', 3), ('INATIVO', 4), ('ONLINE', 5)):
            self.onu(serial, pos=pos, oper='up' if serial == 'ONLINE' else 'down')
        self.cliente('ATIVO_8D', 'Ativo 8 dias')
        self.cliente('ATIVO_2D', 'Ativo 2 dias')
        self.cliente('BLOQUEADO', 'Bloqueado', internet='FA')
        self.cliente('INATIVO', 'Inativo', contrato='I', internet='D')
        self.cliente('ONLINE', 'Online')
        self.snapshot('ATIVO_8D', self.agora - timedelta(days=8), 'up')
        self.snapshot('ATIVO_2D', self.agora - timedelta(days=2), 'up')
        self.snapshot('BLOQUEADO', self.agora - timedelta(days=9), 'up')
        self.snapshot('INATIVO', self.agora - timedelta(days=9), 'up')
        self.queda('ATIVO_8D', self.agora - timedelta(days=8), tipo=OntEvent.TYPE_INATIVA)

        r = self.client.get('/api/desconexoes/offline-ativos/?dias_offline=5').json()
        self.assertEqual([i['serial'] for i in r['itens']], ['ATIVO_8D'])
        item = r['itens'][0]
        self.assertGreaterEqual(item['dias_offline'], 7.9)
        self.assertFalse(item['dias_minimo'])
        self.assertEqual(item['causa'], 'fibra')
        self.assertEqual(r['onus_offline_total'], 4)

    def test_offline_sem_historico_up_marca_dias_como_minimo(self):
        self.onu('NUNCA_UP', oper='down')
        self.cliente('NUNCA_UP', 'Nunca visto online')
        self.snapshot('OUTRA', self.agora - timedelta(days=20), 'up')  # define o início do histórico
        r = self.client.get('/api/desconexoes/offline-ativos/?dias_offline=5').json()
        self.assertEqual(r['total'], 1)
        self.assertTrue(r['itens'][0]['dias_minimo'])
        self.assertEqual(r['itens'][0]['causa'], 'sem_evento')

    def test_offline_sem_contrato_so_com_opcao(self):
        self.onu('PROVISIONADO', oper='down')
        self.cliente('PROVISIONADO', 'Sem contrato', contrato='', internet='', vinculado=False)
        self.snapshot('PROVISIONADO', self.agora - timedelta(days=10), 'up')
        sem = self.client.get('/api/desconexoes/offline-ativos/').json()
        com = self.client.get('/api/desconexoes/offline-ativos/?incluir_sem_contrato=1').json()
        self.assertEqual(sem['total'], 0)
        self.assertEqual(com['total'], 1)

    def test_exige_autenticacao_e_tolera_parametros_invalidos(self):
        r = self.client.get('/api/desconexoes/recorrentes/?janela=abc&min_dias=-1')
        self.assertEqual(r.status_code, 200)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/desconexoes/offline-ativos/').status_code, 401)
