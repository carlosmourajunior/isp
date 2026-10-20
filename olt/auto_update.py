"""
Atualização automática das OLTs.

Roda só no container `scheduler` (manage.py run_scheduler): um único
processo. O APScheduler antigo subia em todo processo Django (cada worker do
gunicorn, rq_worker, syslog_collector...), então ligar o job horário dele
enfileiraria a mesma atualização várias vezes por hora.

Liga/desliga e intervalo ficam no admin (SchedulerConfig) e são relidos a
cada minuto.
"""
import logging

from django.utils import timezone
from django_rq import get_queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from olt.models import Olt, SchedulerConfig

logger = logging.getLogger(__name__)

AUTO_USER = 'Sistema Automático'
PENDING_STATUSES = {'queued', 'started', 'deferred', 'scheduled'}


def _status_name(job):
    status = job.get_status(refresh=False)
    # rq devolve JobStatus (Enum) em algumas versões e str em outras.
    return getattr(status, 'value', status)


def pending_job_ids(queue, job_ids):
    """Jobs da execução anterior que ainda não terminaram."""
    pending = []
    for job_id in job_ids:
        try:
            job = Job.fetch(job_id, connection=queue.connection)
        except NoSuchJobError:
            continue
        if _status_name(job) in PENDING_STATUSES:
            pending.append(job_id)
    return pending


def enqueue_full_update(queue, olts):
    """Mesma sequência do comprehensive_update_task, mas guardando os IDs
    de todos os jobs (lá só o job "pai" é conhecido, e ele termina antes dos
    filhos). Clientes do IXC uma vez só - não é por OLT."""
    from olt import tasks

    steps = [
        (tasks.update_olt_system_task, 'Atualização Sistema OLT', 300),
        (tasks.update_port_occupation_task, 'Atualização de Portas', 1200),
        (tasks.update_onus_task, 'Atualização de ONUs', 1200),
        (tasks.update_mac_task, 'Atualização de MAC', 1200),
    ]
    job_ids = []
    for olt in olts:
        for func, label, timeout in steps:
            job = queue.enqueue(func, olt_id=olt.id, user=AUTO_USER,
                                menu_item=f"{label} ({olt.name}) - automática", job_timeout=timeout)
            job_ids.append(job.id)
    job = queue.enqueue(tasks.update_clientes_task, user=AUTO_USER,
                        menu_item="Atualização de Clientes - automática", job_timeout=1200)
    job_ids.append(job.id)
    return job_ids


def tick(now=None, queue=None):
    """Uma verificação (chamada a cada minuto). Devolve o que aconteceu:
    'disabled', 'waiting', 'skipped', 'no_olts' ou 'enqueued'."""
    now = now or timezone.now()
    config = SchedulerConfig.load()
    config.heartbeat_at = now

    if not config.enabled:
        config.save(update_fields=['heartbeat_at'])
        return 'disabled'

    if config.next_run_at and now < config.next_run_at:
        config.save(update_fields=['heartbeat_at'])
        return 'waiting'

    queue = queue or get_queue('default')
    pending = pending_job_ids(queue, config.last_job_ids or [])
    if pending:
        # Re-tenta a cada minuto até a anterior terminar; loga só na primeira vez.
        if not config.last_run_summary.startswith('Aguardando'):
            logger.warning(f"Atualização automática adiada: {len(pending)} job(s) da execução anterior ainda na fila")
        config.last_run_summary = (f"Aguardando a execução anterior terminar "
                                   f"({len(pending)} job(s) na fila) - verificado {timezone.localtime(now):%d/%m %H:%M}")
        config.save(update_fields=['heartbeat_at', 'last_run_summary'])
        return 'skipped'

    olts = list(Olt.objects.filter(is_active=True).order_by('id'))
    if not olts:
        config.last_run_summary = "Nenhuma OLT ativa cadastrada"
        config.save(update_fields=['heartbeat_at', 'last_run_summary'])
        return 'no_olts'

    job_ids = enqueue_full_update(queue, olts)
    config.last_run_at = now
    config.last_job_ids = job_ids
    config.last_run_summary = (f"Enfileirada em {timezone.localtime(now):%d/%m %H:%M}: "
                               f"{len(olts)} OLT(s), {len(job_ids)} jobs")
    config.save(update_fields=['heartbeat_at', 'last_run_at', 'last_job_ids', 'last_run_summary'])
    logger.info(f"Atualização automática enfileirada: {len(olts)} OLT(s), {len(job_ids)} jobs")
    return 'enqueued'
