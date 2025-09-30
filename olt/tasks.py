from time import sleep
from olt.utils import olt_connector
from django_rq import job, get_queue
import django_rq
from datetime import datetime
import rq
from .client_utils import update_clientes

def add_metadata(job, user, menu_item):
    """Adiciona metadados à task"""
    job.meta['user'] = user
    job.meta['menu_item'] = menu_item
    job.meta['started_at'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    job.save_meta()

@django_rq.job
def update_port_occupation_task(user=None, menu_item=None):
    """Task para atualizar ocupação das portas"""
    connector = olt_connector()
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    job.meta['current_step'] = "Atualizando ocupação das portas"
    job.save_meta()
    
    connector.update_port_ocupation(read_timeout=600, expect_string='typ:isadmin>#')
    return "Atualização de portas concluída"

@django_rq.job
def update_onus_task(user=None, menu_item=None):
    """Task para atualizar ONUs"""
    connector = olt_connector()
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    job.meta['current_step'] = "Atualizando ONUs"
    job.save_meta()
    
    connector.update_all_ports()
    return "Atualização de ONUs concluída"

@django_rq.job
def update_mac_task(user=None, menu_item=None):
    """Task para atualizar endereços MAC"""
    connector = olt_connector()
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    job.meta['current_step'] = "Atualizando endereços MAC"
    job.save_meta()
    
    connector.get_mac_values()
    return "Atualização de MAC concluída"

@django_rq.job
def update_clientes_task(user=None, menu_item=None):
    """Task para atualizar clientes fibra"""
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    job.meta['current_step'] = "Atualizando clientes fibra"
    job.save_meta()
    
    update_clientes()
    return "Atualização de clientes concluída"

@django_rq.job
def update_all_data_task(user=None, menu_item=None):
    """Task para iniciar a sequência de atualizações"""
    queue = get_queue('default')
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    
    # Enfileira cada job na sequência, garantindo FIFO (First In, First Out)
    job.meta['current_step'] = "Iniciando atualização sequencial"
    job.save_meta()
    
    # Executa as tasks em sequência, adicionando ao final da fila
    queue.enqueue(update_port_occupation_task, user=user, menu_item="Atualização de Portas", job_timeout=1200, at_front=False)
    queue.enqueue(update_onus_task, user=user, menu_item="Atualização de ONUs", job_timeout=1200, at_front=False)
    queue.enqueue(update_mac_task, user=user, menu_item="Atualização de MAC", job_timeout=1200, at_front=False)
    queue.enqueue(update_clientes_task, user=user, menu_item="Atualização de Clientes", job_timeout=1200, at_front=False)
    
    return "Sequência de atualizações iniciada"

@django_rq.job
def hourly_update_task():
    """Task para atualização automática a cada hora"""
    from datetime import datetime
    import logging
    
    logger = logging.getLogger(__name__)
    current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    logger.info(f"Iniciando atualização automática às {current_time}")
    
    # Executa a atualização completa como usuário automático
    queue = get_queue('default')
    job = queue.enqueue(
        update_all_data_task, 
        user="Sistema Automático", 
        menu_item="Atualização Automática Horária",
        job_timeout=3600  # 1 hora de timeout
    )
    
    logger.info(f"Atualização automática agendada com ID: {job.id}")
    return f"Atualização automática iniciada às {current_time} - Job ID: {job.id}"
