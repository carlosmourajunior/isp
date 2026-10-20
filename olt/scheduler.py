"""
Status da atualização automática, no formato que a API
(/api/scheduler/status/) e o frontend já esperam.

O disparo em si não acontece mais aqui: roda no container `scheduler`
(olt/auto_update.py + manage.py run_scheduler), configurado no admin em
"Atualização automática". O APScheduler que existia aqui subia em todo
processo Django (cada worker do gunicorn, rq_worker...), então ligar o job
horário dele enfileirava a mesma atualização várias vezes por hora.
"""
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def get_scheduler_status():
    """{'status': 'running'|'not_running'|'stopped', 'jobs': [...]}

    - stopped: atualização automática desligada no admin.
    - running: ligada e o processo do scheduler deu sinal nos últimos 3 min.
    - not_running: ligada, mas o container `scheduler` não está respondendo.
    """
    from olt.models import SchedulerConfig

    config = SchedulerConfig.load()
    if not config.enabled:
        return {"status": "stopped", "jobs": []}

    next_run = config.next_run_at
    if next_run is None or next_run <= timezone.now():
        next_run_text = "na próxima verificação"
    else:
        next_run_text = timezone.localtime(next_run).strftime("%d/%m/%Y %H:%M:%S")

    return {
        "status": "running" if config.scheduler_alive() else "not_running",
        "jobs": [{
            "id": "auto_update",
            "name": "Atualização automática",
            "next_run": next_run_text,
            "trigger": f"a cada {config.interval_minutes} min",
        }],
    }
