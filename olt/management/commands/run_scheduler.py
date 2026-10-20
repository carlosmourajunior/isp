"""
Processo único da atualização automática (container `scheduler`).

A cada minuto relê a configuração do admin (Atualização automática) e, se
estiver ligada e o intervalo tiver passado, enfileira a atualização
completa de todas as OLTs ativas. Ver olt/auto_update.py.
"""
import logging
import signal
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from olt.auto_update import tick

logger = logging.getLogger(__name__)

TICK_SECONDS = 60


class Command(BaseCommand):
    help = 'Executa a atualização automática das OLTs (configurada no admin)'

    def handle(self, *args, **options):
        stopping = {'flag': False}

        def _stop(signum, frame):
            stopping['flag'] = True

        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)

        self.stdout.write("Scheduler iniciado - liga/desliga e intervalo em Admin > Atualização automática")
        last_result = None
        while not stopping['flag']:
            close_old_connections()
            try:
                result = tick()
                if result != last_result or result == 'enqueued':
                    self.stdout.write(f"scheduler: {result}")
                last_result = result
            except Exception as e:
                logger.error(f"Scheduler: falha na verificação: {e}")

            # Dorme até a próxima verificação, mas sai rápido num SIGTERM (deploy).
            for _ in range(TICK_SECONDS):
                if stopping['flag']:
                    break
                time.sleep(1)

        self.stdout.write("Scheduler finalizado")
