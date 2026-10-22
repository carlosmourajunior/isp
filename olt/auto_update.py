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

from datetime import timezone as dt_timezone

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


# Folga além do job_timeout para considerar um job "rodando" como morto.
FOLGA_JOB_MORTO_S = 600
# Job "na fila" há mais que isso não vai mais rodar (fila perdida/limpa).
FILA_ABANDONADA_S = 12 * 3600


def _job_morto(job, agora):
    """Job que o Redis ainda marca como pendente, mas que não vai terminar nunca.

    Acontece quando o rq_worker é reiniciado no meio do job (deploy do Watchtower,
    restart): o status fica 'started' para sempre e o scheduler travaria esperando.
    """
    status = _status_name(job)
    if status == 'started':
        inicio = job.started_at or job.enqueued_at
        limite = (job.timeout or 1200) + FOLGA_JOB_MORTO_S
    elif status in ('queued', 'deferred', 'scheduled'):
        inicio = job.enqueued_at
        limite = FILA_ABANDONADA_S
    else:
        return False
    if inicio is None:
        return False
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=dt_timezone.utc)
    return (agora - inicio).total_seconds() > limite


def pending_job_ids(queue, job_ids, agora=None):
    """Jobs da execução anterior que ainda não terminaram (ignorando os mortos)."""
    agora = agora or timezone.now()
    pending = []
    for job_id in job_ids:
        try:
            job = Job.fetch(job_id, connection=queue.connection)
        except NoSuchJobError:
            continue
        if _status_name(job) in PENDING_STATUSES and not _job_morto(job, agora):
            pending.append(job_id)
    return pending


def enqueue_full_update(queue, olts):
    """Mesma sequência do comprehensive_update_task, mas guardando os IDs
    de todos os jobs (lá só o job "pai" é conhecido, e ele termina antes dos
    filhos). Clientes do IXC (e CTOs) uma vez só - não é por OLT; ao terminar,
    ela enfileira a inferência de CTO de cada OLT."""
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
    # A inferência de CTO de cada OLT é enfileirada pela própria sincronização de
    # clientes, ao terminar (tasks.update_clientes_task).
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
    pending = pending_job_ids(queue, config.last_job_ids or [], agora=now)
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
