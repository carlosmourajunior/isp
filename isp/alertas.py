"""
Alertas de segurança no Telegram.

Só envia se TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID estiverem no .env; sem eles, vira
um log de warning e nada mais. O envio roda numa thread para não atrasar a request,
e cada tipo de alerta tem uma chave de deduplicação: a mesma chave não manda de novo
dentro da janela (cache 'throttle', Redis compartilhado entre os workers do gunicorn).
Se o Redis ou o Telegram falharem, o alerta se perde mas a request segue normal.
"""
import logging
import os
import socket
import threading

import requests
from django.core.cache import caches

logger = logging.getLogger(__name__)

PREFIXO_CACHE = 'alerta:'


def _configurado():
    return bool(os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'))


def _enviar(texto):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    try:
        r = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': os.getenv('TELEGRAM_CHAT_ID'), 'text': texto, 'disable_web_page_preview': True},
            timeout=10,
        )
        if r.status_code != 200:
            logger.error(f'Telegram recusou o alerta ({r.status_code}): {r.text[:200]}')
    except Exception as e:
        logger.error(f'Falha ao enviar alerta ao Telegram: {e}')


def _primeira_vez(chave, janela):
    """True se a chave não foi usada na janela (e marca). Sem Redis, deixa enviar."""
    try:
        return caches['throttle'].add(PREFIXO_CACHE + chave, 1, janela)
    except Exception as e:
        logger.error(f'Cache de alertas indisponível: {e}')
        return True


def contar(chave, janela):
    """Incrementa um contador que expira na janela e devolve o valor. Sem Redis, devolve 0."""
    try:
        cache = caches['throttle']
        k = PREFIXO_CACHE + 'n:' + chave
        if cache.add(k, 1, janela):
            return 1
        return cache.incr(k)
    except Exception as e:
        logger.error(f'Cache de alertas indisponível: {e}')
        return 0


def alertar(texto, chave=None, janela=3600):
    """Manda `texto` ao Telegram. Com `chave`, no máximo um envio por `janela` segundos."""
    logger.warning(f'ALERTA: {texto}')
    if not _configurado():
        return False
    if chave and not _primeira_vez(chave, janela):
        return False
    origem = os.getenv('ALERTA_ORIGEM') or os.getenv('DOMAIN') or socket.gethostname()
    threading.Thread(target=_enviar, args=(f'🛡️ [{origem}] {texto}',), daemon=True).start()
    return True
