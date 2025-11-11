"""
Comando para agendar coleta periódica de dados da OLT
"""
import logging
import time
import signal
import sys
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from olt.utils import OltSystemCollector

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Executa atualização completa de TODOS os dados do sistema (ONUs, Clientes, Portas, OLT) a cada 1 hora'

    def __init__(self):
        super().__init__()
        self.running = True
        
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,  # 1 hora em segundos
            help='Intervalo em segundos entre coletas (padrão: 3600 = 1 hora)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Executa apenas uma vez ao invés de ficar em loop'
        )

    def handle_signal(self, signum, frame):
        """Handle termination signals gracefully"""
        self.stdout.write(
            self.style.WARNING(f'Recebido sinal {signum}, finalizando coleta agendada...')
        )
        self.running = False

    def collect_data(self):
        """Executa uma coleta COMPLETA de todos os dados do sistema"""
        try:
            self.stdout.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando atualização COMPLETA do sistema...")
            
            # Usar a task completa que já existe (inclui ONUs, clientes, portas, OLT, etc.)
            from olt.tasks import update_all_data_task
            import django_rq
            
            # Executar task completa
            queue = django_rq.get_queue('default')
            job = queue.enqueue(
                update_all_data_task,
                user="Sistema Automático",
                menu_item="Atualização Periódica Completa",
                job_timeout=3600  # 1 hora de timeout
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"Atualização completa iniciada - Job ID: {job.id}"
                )
            )
            
            # Aguardar um pouco e verificar se o job foi aceito
            import time
            time.sleep(5)
            
            job.refresh()
            if job.get_status() in ['queued', 'started']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"Job aceito na fila. Status: {job.get_status()}"
                    )
                )
                return True
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"Job com problema. Status: {job.get_status()}"
                    )
                )
                return False
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro na atualização: {str(e)}"
                )
            )
            logger.error(f"Erro na atualização agendada: {str(e)}")
            return False

    def handle(self, *args, **options):
        # Configurar handlers de sinal para parada graceful
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        
        interval = options['interval']
        run_once = options['once']
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Iniciando atualização COMPLETA agendada - "
                f"Intervalo: {interval}s ({interval//3600}h {(interval%3600)//60}m)"
            )
        )
        
        # Executar primeira atualização completa imediatamente
        self.collect_data()
        
        if run_once:
            self.stdout.write(self.style.SUCCESS("Execução única concluída"))
            return
        
        # Loop principal para coletas periódicas
        while self.running:
            try:
                # Aguardar o intervalo especificado
                self.stdout.write(f"Próxima atualização completa em {interval//60} minutos...")
                
                # Sleep em chunks menores para permitir interrupção
                sleep_time = 0
                while sleep_time < interval and self.running:
                    time.sleep(min(60, interval - sleep_time))  # Dormir no máximo 1 minuto por vez
                    sleep_time += 60
                
                if self.running:
                    self.collect_data()
                    
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("Interrompido pelo usuário"))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro no loop principal: {str(e)}"))
                time.sleep(300)  # Aguardar 5 minutos antes de tentar novamente
        
        self.stdout.write(self.style.SUCCESS("Atualização agendada finalizada"))