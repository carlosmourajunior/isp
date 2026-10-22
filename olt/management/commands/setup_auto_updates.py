"""
Mostra/altera a atualização automática pela linha de comando (o mesmo que o
admin em "Atualização automática").

    python manage.py setup_auto_updates --status
    python manage.py setup_auto_updates --start [--interval 120]
    python manage.py setup_auto_updates --stop
"""
from django.core.management.base import BaseCommand

from olt.models import SchedulerConfig
from olt.scheduler import get_scheduler_status


class Command(BaseCommand):
    help = 'Liga/desliga a atualização automática das OLTs'

    def add_arguments(self, parser):
        parser.add_argument('--start', action='store_true', help='Liga a atualização automática')
        parser.add_argument('--stop', action='store_true', help='Desliga a atualização automática')
        parser.add_argument('--status', action='store_true', help='Mostra o status')
        parser.add_argument('--interval', type=int, help='Intervalo em minutos (mínimo 30)')

    def handle(self, *args, **options):
        config = SchedulerConfig.load()
        if options['interval'] is not None:
            config.interval_minutes = max(30, options['interval'])
        if options['start']:
            config.enabled = True
        if options['stop']:
            config.enabled = False
        config.save()

        status = get_scheduler_status()
        self.stdout.write(f"Status: {status['status']} | ligada: {config.enabled} | a cada {config.interval_minutes} min")
        for job in status['jobs']:
            self.stdout.write(f"  Próxima execução: {job['next_run']}")
        self.stdout.write(f"  Última execução: {config.last_run_at or '-'}")
        self.stdout.write(f"  Último sinal do processo: {config.heartbeat_at or '-'}")
        self.stdout.write(f"  Resultado da última verificação: {config.last_run_summary or '-'}")
        if config.enabled and status['status'] == 'not_running':
            self.stdout.write(self.style.WARNING("O container 'scheduler' não está respondendo."))
        self._jobs_do_ultimo_ciclo(config)

    def _jobs_do_ultimo_ciclo(self, config):
        """Diagnóstico: em que pé estão os jobs do último ciclo."""
        from django_rq import get_queue
        from rq.exceptions import NoSuchJobError
        from rq.job import Job

        if not config.last_job_ids:
            return
        queue = get_queue('default')
        self.stdout.write("  Jobs do último ciclo:")
        for job_id in config.last_job_ids:
            try:
                job = Job.fetch(job_id, connection=queue.connection)
            except NoSuchJobError:
                self.stdout.write(f"    {job_id[:8]}  (expirado no Redis)")
                continue
            status = job.get_status()
            status = getattr(status, 'value', status)
            self.stdout.write(f"    {job_id[:8]}  {status:<9} {job.func_name.split('.')[-1]:<30} "
                              f"{job.meta.get('menu_item', '')}")
