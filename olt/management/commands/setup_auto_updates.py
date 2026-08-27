"""
Comando Django para configurar agendamentos automáticos de atualização.
Este comando usa APScheduler para agendar tarefas periódicas.
"""
from django.core.management.base import BaseCommand
from olt.scheduler import start_scheduler, stop_scheduler, get_scheduler_status
import logging


class Command(BaseCommand):
    help = 'Configura agendamentos automáticos para atualizações do sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start',
            action='store_true',
            help='Inicia o scheduler de atualizações automáticas',
        )
        parser.add_argument(
            '--stop',
            action='store_true',
            help='Para o scheduler de atualizações automáticas',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Mostra o status do scheduler',
        )

    def handle(self, *args, **options):
        if options['start']:
            self.start_auto_updates()
        elif options['stop']:
            self.stop_auto_updates()
        elif options['status']:
            self.show_status()
        else:
            self.show_help()

    def start_auto_updates(self):
        """Inicia as atualizações automáticas"""
        try:
            start_scheduler()
            self.stdout.write(
                self.style.SUCCESS('✅ Atualizações automáticas iniciadas!')
            )
            self.stdout.write(
                '   Frequência: A cada hora (minuto 0)'
            )
            self.stdout.write(
                '   Para verificar status: python manage.py setup_auto_updates --status'
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao iniciar atualizações automáticas: {e}')
            )

    def stop_auto_updates(self):
        """Para as atualizações automáticas"""
        try:
            stop_scheduler()
            self.stdout.write(
                self.style.WARNING('⏹️ Atualizações automáticas paradas')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao parar atualizações automáticas: {e}')
            )

    def show_status(self):
        """Mostra o status do scheduler"""
        try:
            status = get_scheduler_status()
            
            if status['status'] == 'stopped':
                self.stdout.write(
                    self.style.WARNING('⏹️ Scheduler parado')
                )
            elif status['status'] == 'not_running':
                self.stdout.write(
                    self.style.WARNING('⚠️ Scheduler não está rodando')
                )
            elif status['status'] == 'running':
                self.stdout.write(
                    self.style.SUCCESS('✅ Scheduler rodando')
                )
                
                if status['jobs']:
                    self.stdout.write('\n📋 Jobs agendados:')
                    for job in status['jobs']:
                        next_run = job['next_run'] or 'Não agendado'
                        self.stdout.write(f"  • {job['name']} - Próxima execução: {next_run}")
                else:
                    self.stdout.write('   Nenhum job agendado')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao verificar status: {e}')
            )

    def show_help(self):
        """Mostra informações de ajuda"""
        self.stdout.write(
            self.style.SUCCESS('🔧 Sistema de Atualizações Automáticas')
        )
        self.stdout.write('')
        self.stdout.write('Comandos disponíveis:')
        self.stdout.write('  --start   : Inicia atualizações automáticas')
        self.stdout.write('  --stop    : Para atualizações automáticas')
        self.stdout.write('  --status  : Mostra status atual')
        self.stdout.write('')
        self.stdout.write('Exemplo:')
        self.stdout.write('  python manage.py setup_auto_updates --start')
        self.stdout.write('')
        self.stdout.write('ℹ️ As atualizações executam a cada hora e incluem:')
        self.stdout.write('   • Atualização de portas')
        self.stdout.write('   • Atualização de ONUs') 
        self.stdout.write('   • Atualização de MACs')
        self.stdout.write('   • Atualização de clientes')