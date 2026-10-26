"""Documentação da API (drf-spectacular) e IP do cliente atrás do proxy (isp/client_ip.py)."""
from unittest import mock

from django.contrib.auth.models import User
from django.test import RequestFactory, SimpleTestCase, TestCase

from isp.client_ip import ip_do_cliente


class DocumentacaoTests(TestCase):

    def test_schema_publico_so_tem_endpoints_de_parceiros(self):
        r = self.client.get('/api/schema/?format=json')
        self.assertEqual(r.status_code, 200)
        caminhos = set(r.json()['paths'])
        self.assertIn('/api/onus/', caminhos)
        self.assertIn('/api/auth/login/', caminhos)
        self.assertIn('/api/olt/system-stats/', caminhos)
        self.assertFalse(any(c.startswith(('/api/vistorias', '/api/ixc', '/api/ctos', '/api/tasks', '/api/olts'))
                             for c in caminhos))
        self.assertNotIn('/api/olt/update-system-data/', caminhos)

    def test_paginas_publicas(self):
        self.assertEqual(self.client.get('/api/docs/').status_code, 200)
        self.assertEqual(self.client.get('/api/redoc/').status_code, 200)

    def test_documentacao_interna_so_admin(self):
        self.assertEqual(self.client.get('/api/schema/interno/').status_code, 403)
        User.objects.create_user('comum', password='p')
        self.client.login(username='comum', password='p')
        self.assertEqual(self.client.get('/api/docs/interno/').status_code, 403)
        User.objects.create_user('admin', password='p', is_staff=True)
        self.client.login(username='admin', password='p')
        self.assertEqual(self.client.get('/api/docs/interno/').status_code, 200)
        r = self.client.get('/api/schema/interno/?format=json')
        self.assertIn('/api/vistorias/', r.json()['paths'])


class IpDoClienteTests(SimpleTestCase):

    def req(self, remoto, xff=None):
        extra = {'REMOTE_ADDR': remoto}
        if xff:
            extra['HTTP_X_FORWARDED_FOR'] = xff
        return RequestFactory().get('/', **extra)

    def test_direto_da_internet_ignora_xff(self):
        # Quem acessa direto não consegue se passar por localhost.
        self.assertEqual(ip_do_cliente(self.req('200.1.2.3', '127.0.0.1')), '200.1.2.3')

    def test_pelo_proxy_usa_o_ip_real(self):
        self.assertEqual(ip_do_cliente(self.req('172.18.0.5', '200.1.2.3')), '200.1.2.3')

    def test_pelo_proxy_ignora_o_que_o_cliente_inventou(self):
        # Cliente mandou "127.0.0.1"; o Caddy acrescentou o IP real à direita.
        self.assertEqual(ip_do_cliente(self.req('172.18.0.5', '127.0.0.1, 200.1.2.3')), '200.1.2.3')

    @mock.patch.dict('os.environ', {'TRUSTED_PROXIES': '10.9.9.9'})
    def test_proxies_configuraveis(self):
        self.assertEqual(ip_do_cliente(self.req('172.18.0.5', '200.1.2.3')), '172.18.0.5')
        self.assertEqual(ip_do_cliente(self.req('10.9.9.9', '200.1.2.3')), '200.1.2.3')
