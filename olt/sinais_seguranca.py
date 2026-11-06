"""
Eventos de segurança que viram alerta no Telegram (isp/alertas.py).

- Falhas de login seguidas do mesmo IP (API JWT e /admin/).
- Login com sucesso de usuário staff/admin.
O bloqueio por IP fora da lista fica em isp/middleware.py.
"""
import os

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver

from isp.alertas import alertar, contar
from isp.client_ip import ip_do_cliente

JANELA_FALHAS = 600  # 10 minutos


def _limite_falhas():
    try:
        return int(os.getenv('ALERTA_FALHAS_LOGIN', '5'))
    except ValueError:
        return 5


def _ip(request):
    return ip_do_cliente(request) if request is not None else 'desconhecido'


@receiver(user_login_failed)
def alerta_falhas_de_login(sender, credentials=None, request=None, **kwargs):
    ip = _ip(request)
    usuario = (credentials or {}).get('username') or '?'
    n = contar(f'falhas:{ip}', JANELA_FALHAS)
    if n >= _limite_falhas():
        alertar(f'{n} falhas de login em 10 min do IP {ip} (último usuário tentado: {usuario}).',
                chave=f'falhas:{ip}', janela=JANELA_FALHAS)


@receiver(user_logged_in)
def alerta_login_admin(sender, request=None, user=None, **kwargs):
    if user is not None and (user.is_staff or user.is_superuser):
        alertar(f'Login de administrador: {user.get_username()} a partir do IP {_ip(request)}.')
