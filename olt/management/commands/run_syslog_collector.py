"""
Escuta syslog (UDP) das OLTs e grava as mensagens + eventos de ONT.

É passivo: a OLT empurra os alarmes, nada aqui abre SSH ou consulta a OLT,
então não conflita com a decisão de manter o scheduler automático desligado.

    python manage.py run_syslog_collector [--port 5140]

Variáveis de ambiente:
- SYSLOG_PORT: porta UDP (padrão 5140; 514 exige root).
- SYSLOG_ALLOWED_IPS: IPs de origem aceitos, separados por vírgula. Vazio
  aceita tudo (útil só em teste).
- SYSLOG_DEFAULT_OLT: nome da OLT usada quando o IP de origem não bate com
  nenhum Olt.host - acontece atrás de NAT/Docker Desktop, que trocam o IP.
"""
import logging
import os
import socketserver
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from olt.models import ONU, Olt, OltSyslogMessage, OntEvent
from olt.syslog_parser import parse_ont_alarm

logger = logging.getLogger('olt.connector')

OLT_CACHE_TTL = 300


class OltResolver:
    """IP de origem -> Olt, com cache (o collector recebe muitas mensagens por minuto)."""

    def __init__(self):
        self._by_ip = {}
        self._default = None
        self._loaded_at = 0

    def get(self, ip):
        if time.monotonic() - self._loaded_at > OLT_CACHE_TTL:
            self._by_ip = {o.host: o for o in Olt.objects.all()}
            default_name = os.getenv('SYSLOG_DEFAULT_OLT', '').strip()
            self._default = Olt.objects.filter(name=default_name).first() if default_name else None
            self._loaded_at = time.monotonic()
        return self._by_ip.get(ip) or self._default


def handle_message(raw, source_ip, resolver):
    close_old_connections()
    now = timezone.now()
    olt = resolver.get(source_ip)
    message = OltSyslogMessage.objects.create(olt=olt, source_ip=source_ip, received_at=now, raw=raw)

    event = parse_ont_alarm(raw)
    if event is None:
        return None

    onu_qs = ONU.objects.filter(pon=event['pon'], position=event['position'])
    if olt:
        onu_qs = onu_qs.filter(olt=olt)
    onu = onu_qs.first()

    created = OntEvent.objects.create(
        olt=olt, message=message, occurred_at=now,
        serial=onu.serial if onu else '', **event,
    )
    message.parsed = True
    message.save(update_fields=['parsed'])
    return created


class Command(BaseCommand):
    help = 'Recebe syslog das OLTs (UDP) e grava eventos de ONT'

    def add_arguments(self, parser):
        parser.add_argument('--port', type=int, default=int(os.getenv('SYSLOG_PORT', '5140')))
        parser.add_argument('--host', default='0.0.0.0')

    def handle(self, *args, **options):
        allowed = {ip.strip() for ip in os.getenv('SYSLOG_ALLOWED_IPS', '').split(',') if ip.strip()}
        resolver = OltResolver()
        stdout = self.stdout

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                source_ip = self.client_address[0]
                if allowed and source_ip not in allowed:
                    return
                raw = self.request[0].decode('utf-8', errors='replace').strip()
                if not raw:
                    return
                try:
                    event = handle_message(raw, source_ip, resolver)
                    if event:
                        stdout.write(f"evento: {event}")
                except Exception as e:
                    logger.error(f"Syslog: falha ao gravar mensagem de {source_ip}: {e} | {raw[:200]}")

        server = socketserver.UDPServer((options['host'], options['port']), Handler)
        self.stdout.write(f"Syslog collector escutando em udp/{options['port']} "
                          f"(origens: {', '.join(sorted(allowed)) or 'todas'})")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
