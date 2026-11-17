"""API com várias OLTs: filtro `?olt=` nos endpoints que somavam tudo, rota de PON com barras,
status de temperatura e dados de acesso das OLTs só para administradores."""
from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from olt.models import ONU, Olt, OltSlot, OltSystemInfo, OltTemperature


class MultiOltApiTests(APITestCase):

    def setUp(self):
        self.client.force_authenticate(User.objects.create_user('u', password='p'))
        self.olt1 = Olt.objects.create(name='OLT 1', host='10.0.0.1', username='admin', password='x')
        self.olt2 = Olt.objects.create(name='OLT 2', host='10.0.0.2', username='admin', password='x')

    def onu(self, olt, pon, pos, serial, oper='up'):
        return ONU.objects.create(olt=olt, pon=pon, position=pos, mac='', serial=serial, oper_state=oper,
                                  desc1='', desc2='', olt_rx_sig=-20.0)

    def temp(self, olt, slot, sensor, graus, ativo=True, tca_low=68, tca_high=73, sd_low=80, sd_high=90):
        return OltTemperature.objects.create(olt=olt, slot_name=slot, sensor_id=sensor, actual_temp=graus,
                                             tca_low=tca_low, tca_high=tca_high, shutdown_low=sd_low,
                                             shutdown_high=sd_high, is_active=ativo)

    # ---- /api/onus/pon/{pon}/ ----
    def test_pon_com_barras_funciona_e_separa_por_olt(self):
        self.onu(self.olt1, '1/1/1/5', 1, 'A1')
        self.onu(self.olt2, '1/1/1/5', 1, 'B1')
        self.onu(self.olt2, '1/1/1/5', 2, 'B2')

        todas = self.client.get('/api/onus/pon/1/1/1/5/').json()
        self.assertEqual(todas['total_onus'], 3)
        so_olt2 = self.client.get(f'/api/onus/pon/1/1/1/5/?olt={self.olt2.id}').json()
        self.assertEqual({o['serial'] for o in so_olt2['onus']}, {'B1', 'B2'})
        codificada = self.client.get('/api/onus/pon/1%2F1%2F1%2F5/')
        self.assertEqual(codificada.status_code, 200)

    def test_pon_inexistente_404_e_olt_invalida_400(self):
        self.assertEqual(self.client.get('/api/onus/pon/1/1/9/9/').status_code, 404)
        self.assertEqual(self.client.get('/api/onus/pon/1/1/1/5/?olt=abc').status_code, 400)

    # ---- stats / busca ----
    def test_onus_stats_e_busca_filtram_por_olt(self):
        self.onu(self.olt1, '1/1/1/1', 1, 'AAA', 'up')
        self.onu(self.olt2, '1/1/1/1', 1, 'AAB', 'down')
        self.onu(self.olt2, '1/1/2/1', 1, 'AAC', 'up')

        geral = self.client.get('/api/onus/stats/').json()
        self.assertEqual(geral['total_onus'], 3)
        olt2 = self.client.get(f'/api/onus/stats/?olt={self.olt2.id}').json()
        self.assertEqual((olt2['total_onus'], olt2['onus_offline']), (2, 1))
        self.assertEqual(set(olt2['estatisticas_por_slot']), {'slot_1', 'slot_2'})

        busca = self.client.get(f'/api/onus/search/?q=AA&olt={self.olt1.id}').json()
        self.assertEqual([o['serial'] for o in busca['resultados']], ['AAA'])
        self.assertEqual(self.client.get('/api/onus/search/?q=AA').json()['total_resultados'], 3)

    # ---- system-info ----
    def test_system_info_escolhe_a_olt_e_padrao_e_a_primeira(self):
        for olt, release in ((self.olt1, 'R1'), (self.olt2, 'R2')):
            OltSystemInfo.objects.create(olt=olt, isam_release=release, uptime_raw='x')
        self.assertEqual(self.client.get('/api/olt/system-info/').json()['isam_release'], 'R1')
        self.assertEqual(self.client.get(f'/api/olt/system-info/?olt={self.olt2.id}').json()['isam_release'], 'R2')
        self.assertEqual(self.client.get('/api/olt/system-info/?olt=999').status_code, 404)
        self.assertEqual(self.client.get('/api/olt/system-info/?olt=x').status_code, 400)

    # ---- system-stats / temperature-alerts ----
    def test_system_stats_filtra_por_olt_e_ignora_sensores_inativos(self):
        OltSystemInfo.objects.create(olt=self.olt1, isam_release='R1', uptime_raw='x')
        OltSystemInfo.objects.create(olt=self.olt2, isam_release='R2', uptime_raw='x')
        for olt in (self.olt1, self.olt2):
            OltSlot.objects.create(olt=olt, slot_name='lt:1/1/1', actual_type='fglt-b', enabled=True,
                                   error_status='no-error', availability='available')
        self.temp(self.olt1, 'lt:1/1/1', 1, 50)
        self.temp(self.olt2, 'lt:1/1/1', 1, 76)           # crítico
        self.temp(self.olt2, 'lt:1/1/1', 2, 72)           # aviso
        self.temp(self.olt2, 'lt:1/1/1', 3, 90, ativo=False)   # sensor que sumiu: não conta

        geral = self.client.get('/api/olt/system-stats/').json()
        self.assertEqual(geral['slots_stats']['total_slots'], 2)
        self.assertEqual(geral['system_info']['isam_release'], 'R1')   # OLT padrão, como antes
        self.assertEqual((geral['temperature_stats']['critical_temperatures'],
                          geral['temperature_stats']['warning_temperatures']), (1, 1))

        olt2 = self.client.get(f'/api/olt/system-stats/?olt={self.olt2.id}').json()
        self.assertEqual(olt2['slots_stats']['total_slots'], 1)
        self.assertEqual(olt2['system_info']['isam_release'], 'R2')
        self.assertEqual(olt2['temperature_stats']['max_temperature'], 76)
        self.assertEqual(olt2['temperature_stats']['normal_temperatures'], 0)

        olt1 = self.client.get(f'/api/olt/system-stats/?olt={self.olt1.id}').json()
        self.assertEqual(olt1['temperature_stats']['critical_temperatures'], 0)

    def test_temperature_alerts_por_olt(self):
        self.temp(self.olt1, 's', 1, 80)
        self.temp(self.olt2, 's', 1, 71)
        self.temp(self.olt2, 's', 2, 99, ativo=False)
        todos = self.client.get('/api/olt/temperature-alerts/').json()
        self.assertEqual((todos['critical_count'], todos['warning_count']), (1, 1))
        olt2 = self.client.get(f'/api/olt/temperature-alerts/?olt={self.olt2.id}').json()
        self.assertEqual((olt2['critical_count'], olt2['warning_count']), (0, 1))
        self.assertEqual(olt2['warning_alerts'][0]['olt_name'], 'OLT 2')

    # ---- status da temperatura ----
    def test_status_da_temperatura_segue_a_escada_de_limites(self):
        def status(graus):
            return self.temp(self.olt1, f's{graus}', 1, graus, tca_low=90, tca_high=95, sd_low=110,
                             sd_high=115).status
        self.assertEqual(status(57), 'NORMAL')         # antes: CRITICAL_LOW
        self.assertEqual(status(90), 'WARNING_LOW')
        self.assertEqual(status(95), 'WARNING_HIGH')
        self.assertEqual(status(110), 'CRITICAL_LOW')
        self.assertEqual(status(115), 'CRITICAL_HIGH')

    def test_temperatures_expoe_status_normal(self):
        self.temp(self.olt1, 's', 1, 40, tca_low=90, tca_high=95, sd_low=110, sd_high=115)
        item = self.client.get('/api/olt/temperatures/').json()['results'][0]
        self.assertEqual((item['status'], item['is_critical'], item['is_warning']), ('NORMAL', False, False))


class DadosDeAcessoDasOltsTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user('admin', password='p', is_staff=True)
        self.comum = User.objects.create_user('comum', password='p')
        Olt.objects.create(name='OLT 1', host='10.9.9.9', username='root-olt', password='x', ssh_port=2222)

    def olts(self, usuario):
        self.client.force_authenticate(usuario)
        r = self.client.get('/api/olts/').json()
        return r['results'] if isinstance(r, dict) else r

    def test_usuario_comum_nao_ve_host_usuario_nem_porta(self):
        olt = self.olts(self.comum)[0]
        self.assertEqual(olt['name'], 'OLT 1')
        for campo in ('host', 'username', 'ssh_port', 'password'):
            self.assertNotIn(campo, olt)

    def test_admin_ve_os_dados_de_acesso_menos_a_senha(self):
        olt = self.olts(self.admin)[0]
        self.assertEqual((olt['host'], olt['username'], olt['ssh_port']), ('10.9.9.9', 'root-olt', 2222))
        self.assertNotIn('password', olt)

    def test_detalhe_tambem_esconde_do_usuario_comum(self):
        self.client.force_authenticate(self.comum)
        olt_id = Olt.objects.get().id
        self.assertNotIn('host', self.client.get(f'/api/olts/{olt_id}/').json())
