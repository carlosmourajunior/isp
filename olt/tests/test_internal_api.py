"""
Testes dos endpoints internos novos, criados para dar suporte ao frontend
React (ver plano de modernização). Diferente de test_api_contract.py, esta
superfície NÃO é o contrato congelado de parceiros - pode evoluir livremente
conforme o frontend precisar.

Importante: os endpoints de disparo de tarefa (`/api/tasks/...`) e de ação
direta na OLT (remover/reset ONU) mexem em filas RQ e equipamento real -
por isso todo teste aqui faz mock de `.delay()` e de `olt_connector`, nunca
deixando um job real cair na fila do worker (que roda contra a OLT/IXC de
verdade neste ambiente).
"""
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from olt.models import ONU, ClienteFibraIxc


class AuthRequiredTests(APITestCase):
    """Todo endpoint novo deve recusar acesso sem token, igual ao resto da API."""

    def test_endpoints_protegidos_exigem_token(self):
        casos = [
            ('get', reverse('api:task_list')),
            ('post', reverse('api:trigger_update_ports')),
            ('post', reverse('api:trigger_update_onus')),
            ('post', reverse('api:trigger_update_mac')),
            ('post', reverse('api:trigger_sync_clientes')),
            ('post', reverse('api:trigger_update_all')),
            ('get', reverse('api:scheduler_status_api')),
            ('get', reverse('api:onu_duplicated_list')),
            ('get', reverse('api:mac_address_list')),
            ('get', reverse('api:ftth_boxes_by_occupancy')),
            ('delete', reverse('api:remove_onu', kwargs={'slot': 1, 'port': 1, 'position': 1})),
            ('post', reverse('api:reset_onu', kwargs={'slot': 1, 'port': 1, 'position': 1})),
        ]
        for metodo, url in casos:
            with self.subTest(url):
                response = getattr(self.client, metodo)(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TaskStatusTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='operador', password='senha-forte-123')
        self.client.force_authenticate(user=self.user)

    def test_task_list_tem_as_quatro_listas_de_jobs(self):
        response = self.client.get(reverse('api:task_list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data.keys()),
            {'running_jobs', 'queued_jobs', 'finished_jobs', 'failed_jobs'},
        )

    def test_scheduler_status_retorna_scheduler_e_queue(self):
        response = self.client.get(reverse('api:scheduler_status_api'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('scheduler', response.data)
        self.assertIn('queue', response.data)


class TriggerTaskTests(APITestCase):
    """Disparo de tasks: garante que enfileira o job certo e nunca deixa vazar `.delay()` real."""

    def setUp(self):
        self.user = User.objects.create_user(username='operador', password='senha-forte-123')
        self.client.force_authenticate(user=self.user)

    def _assert_enfileira(self, url_name, mock_target, menu_item_esperado):
        with patch(mock_target) as mocked_delay:
            mocked_delay.return_value = MagicMock(id='job-id-fake')
            response = self.client.post(reverse(f'api:{url_name}'))

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['job_id'], 'job-id-fake')
        mocked_delay.assert_called_once_with(user='operador', menu_item=menu_item_esperado)

    def test_trigger_update_ports_enfileira_update_port_occupation_task(self):
        self._assert_enfileira(
            'trigger_update_ports', 'olt.api_views.update_port_occupation_task.delay', 'Atualização de Portas'
        )

    def test_trigger_update_onus_enfileira_update_onus_task(self):
        self._assert_enfileira(
            'trigger_update_onus', 'olt.api_views.update_onus_task.delay', 'Atualização de ONUs'
        )

    def test_trigger_update_mac_enfileira_update_mac_task(self):
        self._assert_enfileira(
            'trigger_update_mac', 'olt.api_views.update_mac_task.delay', 'Atualização de MAC'
        )

    def test_trigger_sync_clientes_enfileira_update_clientes_task(self):
        self._assert_enfileira(
            'trigger_sync_clientes', 'olt.api_views.update_clientes_task.delay', 'Atualização de Clientes Fibra'
        )

    def test_trigger_update_all_enfileira_comprehensive_update_task(self):
        self._assert_enfileira(
            'trigger_update_all', 'olt.api_views.comprehensive_update_task.delay', 'Atualizar Todos os Dados Completo'
        )


class OnuActionTests(APITestCase):
    """Remover/reiniciar ONU: exige admin (staff/superuser) e nunca fala com uma OLT de verdade no teste."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin_olt', password='senha-forte-123', is_staff=True)
        self.non_admin = User.objects.create_user(username='operador', password='senha-forte-123')
        ONU.objects.create(
            pon='1/1/1/1', position=5, mac='m1', serial='s1',
            oper_state='up', admin_state='up',
        )

    def test_usuario_sem_admin_recebe_403(self):
        self.client.force_authenticate(user=self.non_admin)
        url = reverse('api:remove_onu', kwargs={'slot': 1, 'port': 1, 'position': 5})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(ONU.objects.filter(pon='1/1/1/1', position=5).exists())

    @patch('olt.api_views.olt_connector')
    def test_admin_remove_onu_chama_a_olt_e_apaga_do_banco(self, mock_connector_cls):
        mock_connector = mock_connector_cls.return_value
        self.client.force_authenticate(user=self.admin)
        url = reverse('api:remove_onu', kwargs={'slot': 1, 'port': 1, 'position': 5})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_connector.remove_onu.assert_called_once_with('1/1/1/1/5')
        self.assertFalse(ONU.objects.filter(pon='1/1/1/1', position=5).exists())

    @patch('olt.api_views.olt_connector')
    def test_admin_reset_onu_chama_a_olt_e_mantem_registro(self, mock_connector_cls):
        mock_connector = mock_connector_cls.return_value
        self.client.force_authenticate(user=self.admin)
        url = reverse('api:reset_onu', kwargs={'slot': 1, 'port': 1, 'position': 5})

        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_connector.reset_onu.assert_called_once_with('1/1/1/1/5')
        self.assertTrue(ONU.objects.filter(pon='1/1/1/1', position=5).exists())


class ReadOnlyListTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='operador', password='senha-forte-123')
        self.client.force_authenticate(user=self.user)

    def test_lista_duplicadas_so_traz_seriais_repetidos(self):
        ONU.objects.create(pon='1/1/1/1', position=1, mac='m1', serial='dup', oper_state='up')
        ONU.objects.create(pon='1/1/1/2', position=2, mac='m2', serial='dup', oper_state='up')
        ONU.objects.create(pon='1/1/1/3', position=3, mac='m3', serial='unico', oper_state='up')

        response = self.client.get(reverse('api:onu_duplicated_list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        seriais = {onu['serial'] for onu in response.data['results']}
        self.assertEqual(seriais, {'dup'})
        self.assertEqual(len(response.data['results']), 2)

    def test_lista_mac_addresses_aceita_busca(self):
        ONU.objects.create(pon='1/1/1/1', position=1, mac='aa:bb:cc', serial='s1', oper_state='up')
        ONU.objects.create(pon='1/1/1/2', position=2, mac='dd:ee:ff', serial='s2', oper_state='up')

        response = self.client.get(reverse('api:mac_address_list'), {'search': 'aa:bb'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['mac'], 'aa:bb:cc')

    def test_ftth_boxes_agrupa_por_caixa_e_ordena_por_ocupacao(self):
        ClienteFibraIxc.objects.create(mac='m1', nome='Cliente 1', id_caixa_ftth='CAIXA-A')
        ClienteFibraIxc.objects.create(mac='m2', nome='Cliente 2', id_caixa_ftth='CAIXA-A')
        ClienteFibraIxc.objects.create(mac='m3', nome='Cliente 3', id_caixa_ftth='CAIXA-B')

        response = self.client.get(reverse('api:ftth_boxes_by_occupancy'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        primeira_caixa = response.data['results'][0]
        self.assertEqual(primeira_caixa['id_caixa_ftth'], 'CAIXA-A')
        self.assertEqual(primeira_caixa['client_count'], 2)
