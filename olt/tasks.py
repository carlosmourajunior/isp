from time import sleep
from olt.utils import olt_connector
from django_rq import job, get_queue
import django_rq
from .models import OltUsers, ONU
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
    
    # Enfileira cada job na sequência, colocando no início da fila
    job.meta['current_step'] = "Iniciando atualização sequencial"
    job.save_meta()
    
    # Executa as tasks em sequência
    queue.enqueue(update_port_occupation_task, user=user, menu_item="Atualização de Portas", job_timeout=1200, at_front=True)
    sleep(5)
    queue.enqueue(update_onus_task, user=user, menu_item="Atualização de ONUs", job_timeout=1200, at_front=True)
    sleep(5)
    queue.enqueue(update_mac_task, user=user, menu_item="Atualização de MAC", job_timeout=1200, at_front=True)
    sleep(5)
    queue.enqueue(update_clientes_task, user=user, menu_item="Atualização de Clientes", job_timeout=1200, at_front=True)
    
    return "Sequência de atualizações iniciada"
