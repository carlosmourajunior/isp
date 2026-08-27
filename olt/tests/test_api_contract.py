"""
Testes de contrato da API sob /api/ - a superfície usada por parceiros
externos, que não pode mudar de formato sem aviso. O objetivo aqui não é
testar regras de negócio a fundo, e sim travar path, autenticação e o
formato exato da resposta: se um desses testes quebrar depois de uma
mudança, é sinal de que a mudança vazou para o contrato público da API.

Referência do que está congelado: API_DOCUMENTATION.md.
"""
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from olt.models import ONU, OltUsers, ClienteFibraIxc, OltSystemInfo


class AuthContractTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='parceiro', password='senha-forte-123')

    def test_login_com_credenciais_validas_retorna_tokens(self):
        url = reverse('api:token_obtain_pair')
        response = self.client.post(url, {'username': 'parceiro', 'password': 'senha-forte-123'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user_info', response.data)

    def test_login_com_credenciais_invalidas_retorna_401(self):
        url = reverse('api:token_obtain_pair')
        response = self.client.post(url, {'username': 'parceiro', 'password': 'errada'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_endpoints_protegidos_exigem_token(self):
        for nome_da_url in ('api:onu_list', 'api:olt_users_list', 'api:clientes_fibra_list', 'api:onu_stats'):
            with self.subTest(nome_da_url):
                response = self.client.get(reverse(nome_da_url))
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedApiContractTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='parceiro', password='senha-forte-123')
        self.client.force_authenticate(user=self.user)

    def test_lista_onus_tem_o_formato_paginado_e_os_campos_documentados(self):
        ONU.objects.create(
            pon='1/1/1/1', position=1, mac='48575443:12345678', serial='FHTT12345678',
            oper_state='up', admin_state='up', olt_rx_sig=-18.5, ont_olt='1500',
            desc1='Cliente Teste', desc2='obs', cliente_fibra=True,
        )

        response = self.client.get(reverse('api:onu_list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for chave in ('count', 'next', 'previous', 'results'):
            self.assertIn(chave, response.data)

        onu = response.data['results'][0]
        campos_esperados = {
            'id', 'pon', 'slot', 'port', 'position', 'mac', 'serial',
            'oper_state', 'admin_state', 'olt_rx_sig', 'ont_olt',
            'desc1', 'desc2', 'cliente_fibra',
        }
        self.assertEqual(set(onu.keys()), campos_esperados)
        self.assertEqual(onu['serial'], 'FHTT12345678')
        self.assertEqual(onu['cliente_fibra'], True)

    def test_lista_olt_users_tem_os_campos_documentados(self):
        from django.utils import timezone
        OltUsers.objects.create(slot=1, port=1, users_connected=42, last_updated=timezone.now())

        response = self.client.get(reverse('api:olt_users_list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data['results'][0]
        self.assertEqual(set(item.keys()), {'id', 'slot', 'port', 'users_connected', 'last_updated'})
        self.assertEqual(item['users_connected'], 42)

    def test_lista_clientes_fibra_tem_os_campos_documentados(self):
        ClienteFibraIxc.objects.create(mac='AA:BB:CC', nome='Cliente X', endereco='Rua 1')

        response = self.client.get(reverse('api:clientes_fibra_list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data['results'][0]
        self.assertEqual(
            set(item.keys()),
            {'id', 'mac', 'nome', 'latitude', 'longitude', 'endereco', 'id_caixa_ftth'},
        )

    def test_stats_de_onus_tem_as_chaves_documentadas(self):
        ONU.objects.create(pon='1/1/1/1', position=1, mac='m1', serial='s1', oper_state='up')
        ONU.objects.create(pon='1/1/2/1', position=1, mac='m2', serial='s2', oper_state='down')

        response = self.client.get(reverse('api:onu_stats'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        chaves_esperadas = {
            'total_onus', 'onus_online', 'onus_offline', 'clientes_fibra',
            'onus_sinal_baixo', 'estatisticas_por_slot', 'percentual_online',
        }
        self.assertEqual(set(response.data.keys()), chaves_esperadas)
        self.assertEqual(response.data['total_onus'], 2)
        self.assertEqual(response.data['onus_online'], 1)

    def test_system_info_tem_os_campos_documentados(self):
        OltSystemInfo.objects.create(
            id=1, isam_release='R6.2.03', uptime_days=958, uptime_hours=12,
            uptime_minutes=26, uptime_seconds=47, uptime_raw='System Up Time: 958 days',
        )

        response = self.client.get(reverse('api:olt_system_info'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data.keys()),
            {
                'id', 'isam_release', 'uptime_days', 'uptime_hours', 'uptime_minutes',
                'uptime_seconds', 'uptime_raw', 'total_uptime_hours', 'last_updated',
            },
        )
        self.assertEqual(response.data['isam_release'], 'R6.2.03')


class RemovedMonitoringEndpointsTests(APITestCase):
    """
    Confirma que a remoção da stack Prometheus/Grafana (não usada pela
    equipe) tirou do ar só o que era dela, e não vazou para o /api/ dos
    parceiros.
    """

    def test_endpoints_de_metricas_e_alertas_nao_existem_mais(self):
        for path in ('/api/metrics/', '/api/alerts/webhook', '/api/alerts/status/', '/api/alerts/test/'):
            with self.subTest(path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_endpoints_de_parceiro_continuam_no_ar(self):
        for nome_da_url in (
            'api:token_obtain_pair', 'api:onu_list', 'api:olt_users_list',
            'api:clientes_fibra_list', 'api:onu_stats', 'api:olt_system_info',
        ):
            with self.subTest(nome_da_url):
                # reverse() já falha com NoReverseMatch se a rota tiver sumido
                self.assertTrue(reverse(nome_da_url))
