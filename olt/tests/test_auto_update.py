"""
Testes da atualização automática (olt/auto_update.py): liga/desliga,
intervalo e não sobrepor execuções. A fila RQ é simulada - nada aqui toca
Redis nem a OLT.
"""
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from olt.auto_update import tick
from olt.models import Olt, SchedulerConfig


class FakeJob:
    def __init__(self, job_id, status='queued'):
        self.id = job_id
        self.status = status

    def get_status(self, refresh=False):
        return self.status


class FakeQueue:
    connection = None

    def __init__(self):
        self.jobs = {}

    def enqueue(self, func, **kwargs):
        job = FakeJob(f"job-{len(self.jobs) + 1}")
        self.jobs[job.id] = job
        return job

    def fetch(self, job_id, connection=None):
        return self.jobs[job_id]


class TickTests(TestCase):

    def setUp(self):
        Olt.objects.create(name='OLT A', host='10.0.0.1', username='u', password='p')
        Olt.objects.create(name='OLT B', host='10.0.0.2', username='u', password='p')
        Olt.objects.create(name='OLT inativa', host='10.0.0.3', username='u', password='p', is_active=False)
        self.queue = FakeQueue()
        patcher = mock.patch('olt.auto_update.Job.fetch', side_effect=self.queue.fetch)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.now = timezone.now()

    def _ligar(self, minutos=120):
        config = SchedulerConfig.load()
        config.enabled = True
        config.interval_minutes = minutos
        config.save()

    def test_desligado_nao_enfileira_mas_registra_sinal(self):
        self.assertEqual(tick(now=self.now, queue=self.queue), 'disabled')
        self.assertEqual(self.queue.jobs, {})
        self.assertEqual(SchedulerConfig.load().heartbeat_at, self.now)

    def test_primeira_execucao_enfileira_todas_olts_ativas(self):
        self._ligar()
        self.assertEqual(tick(now=self.now, queue=self.queue), 'enqueued')
        # 4 etapas por OLT ativa (2) + clientes do IXC uma vez só + inferência de CTO por OLT (2)
        self.assertEqual(len(self.queue.jobs), 11)
        config = SchedulerConfig.load()
        self.assertEqual(config.last_run_at, self.now)
        self.assertEqual(len(config.last_job_ids), 11)

    def test_dentro_do_intervalo_espera(self):
        self._ligar(minutos=120)
        tick(now=self.now, queue=self.queue)
        self.assertEqual(tick(now=self.now + timedelta(minutes=60), queue=self.queue), 'waiting')
        self.assertEqual(len(self.queue.jobs), 11)

    def test_nao_sobrepoe_se_anterior_ainda_na_fila(self):
        self._ligar(minutos=30)
        tick(now=self.now, queue=self.queue)
        self.queue.jobs['job-11'].status = 'started'
        self.assertEqual(tick(now=self.now + timedelta(minutes=31), queue=self.queue), 'skipped')
        self.assertEqual(len(self.queue.jobs), 11)

    def test_enfileira_de_novo_quando_anterior_terminou(self):
        self._ligar(minutos=30)
        tick(now=self.now, queue=self.queue)
        for job in self.queue.jobs.values():
            job.status = 'finished'
        self.assertEqual(tick(now=self.now + timedelta(minutes=31), queue=self.queue), 'enqueued')
        self.assertEqual(len(self.queue.jobs), 22)

    def test_desligar_pelo_admin_para_na_hora(self):
        self._ligar(minutos=30)
        tick(now=self.now, queue=self.queue)
        config = SchedulerConfig.load()
        config.enabled = False
        config.save()
        self.assertEqual(tick(now=self.now + timedelta(minutes=31), queue=self.queue), 'disabled')


class SchedulerStatusTests(TestCase):
    """Formato consumido por /api/scheduler/status/ e pela tela Scheduler do frontend."""

    def test_desligado(self):
        from olt.scheduler import get_scheduler_status
        self.assertEqual(get_scheduler_status(), {'status': 'stopped', 'jobs': []})

    def test_ligado_com_processo_vivo(self):
        from olt.scheduler import get_scheduler_status
        config = SchedulerConfig.load()
        config.enabled = True
        config.heartbeat_at = timezone.now()
        config.save()
        status = get_scheduler_status()
        self.assertEqual(status['status'], 'running')
        self.assertEqual(len(status['jobs']), 1)
        self.assertEqual(set(status['jobs'][0]), {'id', 'name', 'next_run', 'trigger'})

    def test_ligado_sem_processo(self):
        from olt.scheduler import get_scheduler_status
        config = SchedulerConfig.load()
        config.enabled = True
        config.heartbeat_at = timezone.now() - timedelta(minutes=10)
        config.save()
        self.assertEqual(get_scheduler_status()['status'], 'not_running')
