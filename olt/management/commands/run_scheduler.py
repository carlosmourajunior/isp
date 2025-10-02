"""
Comando Django para executar o scheduler de tarefas de forma contínua.
Este comando mantém o scheduler rodando em background.
"""
from django.core.management.base import BaseCommand
from olt.scheduler import start_scheduler, stop_scheduler
import time
import signal
import sys
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Executa o scheduler de tarefas automáticas de forma contínua'

    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Executa como daemon em background',
        )

    def handle(self, *args, **options):
        # Configurar handler para sinais de sistema
        def signal_handler(signum, frame):
            self.stdout.write(
                self.style.WARNING('\n🛑 Recebido sinal de parada, finalizando scheduler...')
            )
            stop_scheduler()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Inicia o scheduler
            self.stdout.write(
                self.style.SUCCESS('🔄 Iniciando scheduler de tarefas automáticas...')
            )
            start_scheduler()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Scheduler iniciado com sucesso!')
            )
            self.stdout.write('   Frequência: A cada hora (minuto 0)')
            self.stdout.write('   Para parar: Ctrl+C ou SIGTERM')
            
            # Mantém o processo rodando
            if options['daemon']:
                self.stdout.write('🔄 Executando em modo daemon...')
            
            while True:
                time.sleep(60)  # Verifica a cada minuto
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n🛑 Scheduler interrompido pelo usuário')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro no scheduler: {e}')
            )
        finally:
            stop_scheduler()
            self.stdout.write(
                self.style.SUCCESS('✅ Scheduler finalizado')
            )