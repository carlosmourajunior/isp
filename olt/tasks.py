from time import sleep
from olt.utils import olt_connector, OltSystemCollector
from olt.models import Olt
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


def _get_olt(olt_id):
    """Resolve a OLT alvo da task. olt_id=None cai no fallback de
    get_default_olt() (primeira OLT ativa) - mantém o comportamento de
    antes do multi-OLT pra quem ainda dispara sem escolher uma OLT."""
    return Olt.objects.get(id=olt_id) if olt_id else None


@django_rq.job
def update_port_occupation_task(olt_id=None, user=None, menu_item=None):
    """Task para atualizar ocupação das portas"""
    connector = olt_connector(_get_olt(olt_id))
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    job.meta['current_step'] = f"Atualizando ocupação das portas ({connector.olt.name})"
    job.save_meta()

    connector.update_port_ocupation(read_timeout=600, expect_string='typ:isadmin>#')
    return "Atualização de portas concluída"

@django_rq.job
def update_onus_task(olt_id=None, user=None, menu_item=None):
    """Task para atualizar ONUs"""
    connector = olt_connector(_get_olt(olt_id))
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    job.meta['current_step'] = f"Atualizando ONUs ({connector.olt.name})"
    job.save_meta()

    connector.update_all_ports()
    job.meta['current_step'] = f"Atualizando sinal óptico das ONUs ({connector.olt.name})"
    job.save_meta()
    connector.update_optics()
    return "Atualização de ONUs concluída"

@django_rq.job
def update_mac_task(olt_id=None, user=None, menu_item=None):
    """Task para atualizar endereços MAC"""
    connector = olt_connector(_get_olt(olt_id))
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    job.meta['current_step'] = f"Atualizando endereços MAC ({connector.olt.name})"
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
def update_all_data_task(olt_id=None, user=None, menu_item=None):
    """Task para iniciar a sequência de atualizações de uma OLT (incluindo dados da OLT)"""
    queue = get_queue('default')
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)

    olt = _get_olt(olt_id) or Olt.objects.filter(is_active=True).order_by('id').first()
    if olt is None:
        job.meta['current_step'] = "Nenhuma OLT ativa cadastrada"
        job.save_meta()
        return "Nenhuma OLT ativa cadastrada"

    # Enfileira cada job na sequência, garantindo FIFO (First In, First Out)
    job.meta['current_step'] = f"Iniciando atualização sequencial completa ({olt.name})"
    job.save_meta()

    # Executa as tasks em sequência, adicionando ao final da fila
    queue.enqueue(update_olt_system_task, olt_id=olt.id, user=user, menu_item="Atualização Sistema OLT", job_timeout=300, at_front=False)
    queue.enqueue(update_port_occupation_task, olt_id=olt.id, user=user, menu_item="Atualização de Portas", job_timeout=1200, at_front=False)
    queue.enqueue(update_onus_task, olt_id=olt.id, user=user, menu_item="Atualização de ONUs", job_timeout=1200, at_front=False)
    queue.enqueue(update_mac_task, olt_id=olt.id, user=user, menu_item="Atualização de MAC", job_timeout=1200, at_front=False)
    queue.enqueue(update_clientes_task, user=user, menu_item="Atualização de Clientes", job_timeout=1200, at_front=False)

    return "Sequência de atualizações completa iniciada"

@django_rq.job
def hourly_update_task():
    """Task para atualização automática a cada hora - roda pra todas as OLTs ativas"""
    from datetime import datetime
    import logging

    logger = logging.getLogger(__name__)
    current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    logger.info(f"Iniciando atualização automática às {current_time}")

    # Executa a atualização completa incluindo dados da OLT, uma vez por OLT ativa
    queue = get_queue('default')
    active_olt_ids = list(Olt.objects.filter(is_active=True).values_list('id', flat=True))
    job_ids = []
    for olt_id in active_olt_ids:
        job = queue.enqueue(
            comprehensive_update_task,
            olt_id=olt_id,
            user="Sistema Automático",
            menu_item="Atualização Automática Horária",
            job_timeout=3600  # 1 hora de timeout
        )
        job_ids.append(job.id)

    logger.info(f"Atualização automática completa agendada para {len(active_olt_ids)} OLT(s) - Job IDs: {job_ids}")
    return f"Atualização automática completa iniciada às {current_time} - Job IDs: {job_ids}"


@django_rq.job
def update_olt_system_task(olt_id=None, user=None, menu_item=None):
    """Task para atualizar informações do sistema OLT"""
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)

    try:
        collector = OltSystemCollector(_get_olt(olt_id))
        job.meta['current_step'] = f"Coletando informações do sistema OLT ({collector.olt.name})"
        job.save_meta()
        result = collector.collect_all_system_data()

        if result:
            job.meta['current_step'] = "Dados do sistema OLT atualizados com sucesso"
            job.save_meta()
            return {
                'status': 'success',
                'message': 'Dados do sistema OLT atualizados com sucesso',
                'system_info': result['system_info'] is not None,
                'slots_count': result['slots'].count() if result['slots'] else 0,
                'temperatures_count': result['temperatures'].count() if result['temperatures'] else 0
            }
        else:
            job.meta['current_step'] = "Falha ao coletar dados da OLT"
            job.save_meta()
            return {
                'status': 'error',
                'message': 'Falha ao coletar dados da OLT'
            }
            
    except Exception as e:
        error_msg = f"Erro ao atualizar dados da OLT: {str(e)}"
        job.meta['current_step'] = error_msg
        job.save_meta()
        return {
            'status': 'error',
            'message': error_msg
        }


@django_rq.job
def comprehensive_update_task(olt_id=None, user=None, menu_item=None):
    """Task para atualização completa de uma OLT (portas, ONUs, MAC, sistema e clientes fibra)"""
    from django.db import connections

    # Fecha conexões antes de iniciar
    for conn in connections.all():
        conn.close()

    queue = get_queue('default')
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)

    olt = _get_olt(olt_id) or Olt.objects.filter(is_active=True).order_by('id').first()
    if olt is None:
        job.meta['current_step'] = "Nenhuma OLT ativa cadastrada"
        job.save_meta()
        return "Nenhuma OLT ativa cadastrada"

    job.meta['current_step'] = f"Iniciando atualização completa ({olt.name})"
    job.save_meta()

    try:
        # Executa as tasks em sequência com intervalos menores
        queue.enqueue(update_olt_system_task, olt_id=olt.id, user=user, menu_item=f"Atualização Sistema OLT ({olt.name})", job_timeout=300, at_front=False)
        sleep(2)  # Pequena pausa entre enqueue
        queue.enqueue(update_port_occupation_task, olt_id=olt.id, user=user, menu_item=f"Atualização de Portas ({olt.name})", job_timeout=1200, at_front=False)
        sleep(2)
        queue.enqueue(update_onus_task, olt_id=olt.id, user=user, menu_item=f"Atualização de ONUs ({olt.name})", job_timeout=1200, at_front=False)
        sleep(2)
        queue.enqueue(update_mac_task, olt_id=olt.id, user=user, menu_item=f"Atualização de MAC ({olt.name})", job_timeout=1200, at_front=False)
        sleep(2)
        queue.enqueue(update_clientes_task, user=user, menu_item="Atualização de Clientes", job_timeout=1200, at_front=False)

        return f"Sequência de atualizações completa iniciada ({olt.name})"

    except Exception as e:
        job.meta['current_step'] = f"Erro: {str(e)}"
        job.save_meta()
        # Fecha conexões em caso de erro
        for conn in connections.all():
            conn.close()
        raise
