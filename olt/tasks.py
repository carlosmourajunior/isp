from olt.utils import olt_connector
from django_rq import job
import django_rq
from .models import OltUsers, ONU
from datetime import datetime
import rq

def add_metadata(job, user, menu_item):
    """Adiciona metadados à task"""
    job.meta['user'] = user
    job.meta['menu_item'] = menu_item
    job.meta['started_at'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    job.save_meta()

@job('default')
def update_mac_values_task(user=None, menu_item=None):
    connector = olt_connector()
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    connector.get_mac_values()

@job('default')
def update_port_occupation_task(user=None, menu_item=None):
    connector = olt_connector()
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    connector.update_port_ocupation(read_timeout=600, expect_string='typ:isadmin>#')

@django_rq.job
def update_users_task(user=None, menu_item=None):
    """Task para atualizar os usuários da OLT usando RQ"""
    connector = olt_connector()
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    connector.update_port_ocupation(read_timeout=600, expect_string='typ:isadmin>#')
    return "Atualização de usuários concluída com sucesso"

@django_rq.job
def update_all_onus(user=None, menu_item=None):
    """Task to update all ONUs using RQ"""
    connector = olt_connector()
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    connector.update_all_ports()
    return "ONUs updated successfully"

@django_rq.job
def update_port_onus(slot, port, user=None, menu_item=None):
    """Task to update ONUs for a specific port"""
    connector = olt_connector()
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    connector.update_port(slot, port)
    return f"ONUs updated for port {slot}/{port}"
