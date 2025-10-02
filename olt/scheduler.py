"""
Sistema de agendamento automático usando APScheduler.
Este módulo gerencia a execução automática de tarefas de atualização.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_rq import get_queue
from django.conf import settings
from datetime import datetime
import atexit

logger = logging.getLogger(__name__)

# Instância global do scheduler
scheduler = None

def start_scheduler():
    """Inicia o scheduler de tarefas automáticas"""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler já está rodando")
        return
    
    try:
        scheduler = BackgroundScheduler(daemon=True)
        
        # Adiciona job para execução a cada hora
        scheduler.add_job(
            func=schedule_hourly_update,
            trigger=CronTrigger(minute=0),  # A cada hora no minuto 0
            id='hourly_update',
            name='Atualização Automática Horária',
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("✅ Scheduler iniciado - Atualizações automáticas configuradas para executar a cada hora")
        
        # Registra função para parar o scheduler ao fechar a aplicação
        atexit.register(stop_scheduler)
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar scheduler: {e}")

def stop_scheduler():
    """Para o scheduler"""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Scheduler parado")

def schedule_hourly_update():
    """Agenda uma atualização completa na fila do RQ (incluindo dados da OLT)"""
    try:
        queue = get_queue('default')
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Importa aqui para evitar import circular
        from olt.tasks import comprehensive_update_task
        
        job = queue.enqueue(
            comprehensive_update_task,
            user="Sistema Automático",
            menu_item="Atualização Automática Horária Completa",
            job_timeout=3600  # 1 hora de timeout
        )
        
        logger.info(f"🔄 Atualização automática completa (incluindo OLT) agendada às {current_time} - Job ID: {job.id}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao agendar atualização automática: {e}")

def get_scheduler_status():
    """Retorna o status do scheduler"""
    global scheduler
    
    if scheduler is None:
        return {"status": "stopped", "jobs": []}
    
    if not scheduler.running:
        return {"status": "not_running", "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.strftime("%d/%m/%Y %H:%M:%S") if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "status": "running",
        "jobs": jobs
    }