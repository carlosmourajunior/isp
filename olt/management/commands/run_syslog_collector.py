"""
Escuta syslog (UDP) das OLTs e grava as mensagens + eventos de ONT.

É passivo: a OLT empurra os alarmes, nada aqui abre SSH ou consulta a OLT,
então não conflita com a decisão de manter o scheduler automático desligado.

    python manage.py run_syslog_collector [--port 5140]

Variáveis de ambiente:
- SYSLOG_PORT: porta UDP (padrão 5140; 514 exige root).
- SYSLOG_ALLOWED_IPS: IPs de origem aceitos, separados por vírgula. Vazio
  aceita tudo (útil só em teste).
- SYSLOG_OLT_BY_HOSTNAME: hostname do cabeçalho do syslog -> nome da OLT.
  Preferencial: funciona mesmo quando várias OLTs saem pelo mesmo IP de
  NAT. Formato: "VIA01_OURO_FINO=OLT 1;VIA01_BORDA=OLT 2".
- SYSLOG_OLT_BY_IP: mapa IP de origem -> nome da OLT, para quando a OLT
  chega por NAT com um IP diferente do Olt.host. Mesmo formato.
- SYSLOG_DEFAULT_OLT: nome da OLT usada quando o IP de origem não bate com
  nada acima - útil só em teste (Docker Desktop troca o IP de origem).
"""
import logging
import os
import socketserver
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone

from olt.models import ONU, Olt, OltSyslogMessage, OntEvent
from olt.syslog_parser import extract_hostname, parse_ont_alarm

logger = logging.getLogger('olt.connector')

OLT_CACHE_TTL = 300


class OltResolver:
    """Hostname/IP de origem -> Olt, com cache (o collector recebe muitas mensagens por minuto)."""

    def __init__(self):
        self._by_hostname = {}
        self._by_ip = {}
        self._default = None
        self._loaded_at = 0

    @staticmethod
    def _mapping_from_env(var, olts_by_name):
        mapping = {}
        for pair in os.getenv(var, '').split(';'):
            key, sep, name = pair.partition('=')
            if not sep:
                continue
            olt = olts_by_name.get(name.strip())
            if olt:
                mapping[key.strip()] = olt
            else:
                logger.warning(f"Syslog: {var} aponta para OLT inexistente: '{name.strip()}'")
        return mapping

    def _reload(self):
        olts = list(Olt.objects.all())
        by_name = {o.name: o for o in olts}
        self._by_hostname = self._mapping_from_env('SYSLOG_OLT_BY_HOSTNAME', by_name)
        self._by_ip = {o.host: o for o in olts}
        self._by_ip.update(self._mapping_from_env('SYSLOG_OLT_BY_IP', by_name))
        default_name = os.getenv('SYSLOG_DEFAULT_OLT', '').strip()
        self._default = by_name.get(default_name) if default_name else None
        self._loaded_at = time.monotonic()

    def get(self, ip, hostname=''):
        if time.monotonic() - self._loaded_at > OLT_CACHE_TTL:
            self._reload()
        return self._by_hostname.get(hostname) or self._by_ip.get(ip) or self._default


def handle_message(raw, source_ip, resolver):
    close_old_connections()
    now = timezone.now()
    olt = resolver.get(source_ip, extract_hostname(raw))
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
