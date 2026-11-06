"""Alertas de segurança no Telegram (isp/alertas.py, olt/sinais_seguranca.py, middleware de IP)."""
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import caches
from django.test import RequestFactory, TestCase, override_settings

from isp import alertas
from isp.middleware import IPWhitelistMiddleware

CACHES_TESTE = {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'padrao'},
    'throttle': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'alertas'},
}
ENV = {'TELEGRAM_BOT_TOKEN': 't', 'TELEGRAM_CHAT_ID': '1', 'ALERTA_ORIGEM': 'teste'}


class _SemThread:
    """Roda o envio na hora, para o teste ver a chamada."""
    def __init__(self, target, args, daemon):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


@override_settings(CACHES=CACHES_TESTE)
@mock.patch.object(alertas.threading, 'Thread', _SemThread)
@mock.patch.object(alertas.requests, 'post')
class AlertasTests(TestCase):

    def setUp(self):
        caches['throttle'].clear()

    @mock.patch.dict('os.environ', {}, clear=True)
    def test_sem_token_nao_envia(self, post):
        self.assertFalse(alertas.alertar('x'))
        post.assert_not_called()

    @mock.patch.dict('os.environ', ENV)
    def test_envia_com_origem(self, post):
        post.return_value.status_code = 200
        self.assertTrue(alertas.alertar('teste de alerta'))
        enviado = post.call_args.kwargs['json']
        self.assertEqual(enviado['chat_id'], '1')
        self.assertIn('[teste] teste de alerta', enviado['text'])

    @mock.patch.dict('os.environ', ENV)
    def test_mesma_chave_nao_repete_na_janela(self, post):
        post.return_value.status_code = 200
        self.assertTrue(alertas.alertar('a', chave='k'))
        self.assertFalse(alertas.alertar('a', chave='k'))
        self.assertEqual(post.call_count, 1)

    @mock.patch.dict('os.environ', ENV)
    def test_falha_do_telegram_nao_estoura(self, post):
        post.side_effect = Exception('rede caiu')
        alertas.alertar('x')  # não levanta

    @mock.patch.dict('os.environ', ENV)
    def test_falhas_de_login_alertam_no_limite(self, post):
        post.return_value.status_code = 200
        User.objects.create_user('u', password='certa')
        for _ in range(4):
            self.client.login(username='u', password='errada')
        post.assert_not_called()
        self.client.login(username='u', password='errada')
        self.assertEqual(post.call_count, 1)
        self.assertIn('5 falhas de login', post.call_args.kwargs['json']['text'])
        self.client.login(username='u', password='errada')  # mesma janela: não repete
        self.assertEqual(post.call_count, 1)

    @mock.patch.dict('os.environ', ENV)
    def test_login_de_admin_alerta(self, post):
        post.return_value.status_code = 200
        User.objects.create_user('comum', password='p')
        self.client.login(username='comum', password='p')
        post.assert_not_called()
        User.objects.create_user('chefe', password='p', is_staff=True)
        self.client.login(username='chefe', password='p')
        self.assertIn('Login de administrador: chefe', post.call_args.kwargs['json']['text'])

    @mock.patch.dict('os.environ', ENV)
    def test_ip_bloqueado_so_alerta_quando_insiste(self, post):
        post.return_value.status_code = 200
        mw = IPWhitelistMiddleware(lambda r: None)
        rf = RequestFactory()
        with mock.patch.object(mw, 'get_allowed_ips', return_value=['10.0.0.0/8']):
            r = mw(rf.get('/api/onus/', REMOTE_ADDR='203.0.113.9'))
            self.assertEqual(r.status_code, 403)
            post.assert_not_called()  # um GET isolado (robô) não alerta
            mw(rf.post('/api/auth/login/', REMOTE_ADDR='203.0.113.9'))
            self.assertEqual(post.call_count, 1)
            self.assertIn('203.0.113.9', post.call_args.kwargs['json']['text'])
