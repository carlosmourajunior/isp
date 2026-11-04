import logging

from django.core.cache import caches
from rest_framework.throttling import SimpleRateThrottle

from isp.client_ip import ip_do_cliente

logger = logging.getLogger(__name__)


class LoginRateThrottle(SimpleRateThrottle):
    """
    Limita tentativas de login por IP (taxa em THROTTLE_RATES['login']).

    Usa o cache 'throttle' (Redis, compartilhado entre os workers do gunicorn) e
    o IP real via ip_do_cliente - o get_ident do DRF confiaria em qualquer
    X-Forwarded-For. Se o Redis cair, deixa passar em vez de derrubar o login.
    """
    scope = 'login'

    def __init__(self):
        self.cache = caches['throttle']
        super().__init__()

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': ip_do_cliente(request)}

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception as e:
            logger.error(f"Throttle de login indisponível, liberando a tentativa: {e}")
            return True
