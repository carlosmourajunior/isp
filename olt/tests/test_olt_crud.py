"""
Testes do CRUD de OLTs (/api/olts/) - o cadastro que viabiliza múltiplas
OLTs no sistema (antes, só existia uma OLT fixa via variáveis de ambiente).
Cobre o que importa de segurança aqui: a senha SSH nunca vaza numa resposta
de leitura, e só admin pode criar/editar/remover.
"""
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from olt.models import Olt
from olt.utils import build_connect_kwargs


class OltCrudTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='senha-forte-123', is_staff=True)
        self.usuario_comum = User.objects.create_user(username='comum', password='senha-forte-123')
        self.olt = Olt.objects.create(
            name='OLT 1', host='192.168.1.1', username='admin', password='segredo-olt',
        )

    def test_listar_exige_autenticacao(self):
        response = self.client.get(reverse('api:olt_list_create'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_usuario_comum_consegue_listar_mas_senha_nao_aparece(self):
        self.client.force_authenticate(user=self.usuario_comum)
        response = self.client.get(reverse('api:olt_list_create'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        olts = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        self.assertEqual(len(olts), 1)
        self.assertNotIn('password', olts[0])
        self.assertEqual(olts[0]['name'], 'OLT 1')

    def test_usuario_comum_nao_pode_criar_olt(self):
        self.client.force_authenticate(user=self.usuario_comum)
        response = self.client.post(reverse('api:olt_list_create'), {
            'name': 'OLT 2', 'host': '192.168.1.2', 'username': 'admin', 'password': 'segredo',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Olt.objects.count(), 1)

    def test_admin_cria_olt_e_senha_fica_criptografada_no_banco(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('api:olt_list_create'), {
            'name': 'OLT 2', 'host': '192.168.1.2', 'username': 'admin', 'password': 'segredo-nova',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)

        nova = Olt.objects.get(name='OLT 2')
        self.assertEqual(nova.password, 'segredo-nova')  # decriptado via ORM

        from django.db import connection
        with connection.cursor() as cur:
            cur.execute('SELECT password FROM olt_olt WHERE id = %s', [nova.id])
            valor_bruto = cur.fetchone()[0]
        self.assertNotEqual(valor_bruto, 'segredo-nova')

    def test_usuario_comum_nao_pode_editar_nem_remover(self):
        self.client.force_authenticate(user=self.usuario_comum)
        url = reverse('api:olt_detail', args=[self.olt.id])

        response_put = self.client.patch(url, {'name': 'Renomeada'}, format='json')
        self.assertEqual(response_put.status_code, status.HTTP_403_FORBIDDEN)

        response_delete = self.client.delete(url)
        self.assertEqual(response_delete.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Olt.objects.filter(id=self.olt.id).exists())

    def test_admin_edita_olt_sem_informar_senha_mantem_a_senha_atual(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('api:olt_detail', args=[self.olt.id])

        response = self.client.patch(url, {'name': 'OLT 1 Renomeada'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.olt.refresh_from_db()
        self.assertEqual(self.olt.name, 'OLT 1 Renomeada')
        self.assertEqual(self.olt.password, 'segredo-olt')

    def test_build_connect_kwargs_usa_dados_da_olt_cadastrada(self):
        kwargs = build_connect_kwargs(self.olt)
        self.assertEqual(kwargs['host'], '192.168.1.1')
        self.assertEqual(kwargs['username'], 'admin')
        self.assertEqual(kwargs['password'], 'segredo-olt')
