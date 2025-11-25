from time import sleep
from olt.utils import olt_connector, OltSystemCollector
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
def collect_alarms_task(user=None, menu_item=None):
    """Task para coletar alarmes da OLT"""
    connector = olt_connector()
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    job.meta['current_step'] = "Coletando alarmes da OLT"
    job.save_meta()
    
    collected_count = connector.collect_all_alarms()
    return f"Coleta de alarmes concluída - {collected_count} alarmes coletados"

@django_rq.job
def update_all_data_task(user=None, menu_item=None):
    """Task para iniciar a sequência de atualizações (incluindo dados da OLT)"""
    queue = get_queue('default')
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    
    # Enfileira cada job na sequência, garantindo FIFO (First In, First Out)
    job.meta['current_step'] = "Iniciando atualização sequencial completa"
    job.save_meta()
    
    # Executa as tasks em sequência, adicionando ao final da fila
    queue.enqueue(update_olt_system_task, user=user, menu_item="Atualização Sistema OLT", job_timeout=300, at_front=False)
    queue.enqueue(update_port_occupation_task, user=user, menu_item="Atualização de Portas", job_timeout=1200, at_front=False)
    queue.enqueue(update_onus_task, user=user, menu_item="Atualização de ONUs", job_timeout=1200, at_front=False)
    queue.enqueue(update_mac_task, user=user, menu_item="Atualização de MAC", job_timeout=1200, at_front=False)
    queue.enqueue(update_clientes_task, user=user, menu_item="Atualização de Clientes", job_timeout=1200, at_front=False)
    queue.enqueue(collect_alarms_task, user=user, menu_item="Coleta de Alarmes", job_timeout=600, at_front=False)
    
    return "Sequência de atualizações completa iniciada"

@django_rq.job
def hourly_update_task():
    """Task para atualização automática a cada hora"""
    from datetime import datetime
    import logging
    
    logger = logging.getLogger(__name__)
    current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    logger.info(f"Iniciando atualização automática às {current_time}")
    
    # Executa a atualização completa incluindo dados da OLT
    queue = get_queue('default')
    job = queue.enqueue(
        comprehensive_update_task, 
        user="Sistema Automático", 
        menu_item="Atualização Automática Horária",
        job_timeout=3600  # 1 hora de timeout
    )
    
    logger.info(f"Atualização automática completa agendada com ID: {job.id}")
    return f"Atualização automática completa iniciada às {current_time} - Job ID: {job.id}"


@django_rq.job
def update_olt_system_task(user=None, menu_item=None):
    """Task para atualizar informações do sistema OLT"""
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    job.meta['current_step'] = "Coletando informações do sistema OLT"
    job.save_meta()
    
    try:
        collector = OltSystemCollector()
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
def comprehensive_update_task(user=None, menu_item=None):
    """Task para atualização completa incluindo dados da OLT"""
    from django.db import connections
    
    # Fecha conexões antes de iniciar
    for conn in connections.all():
        conn.close()
    
    queue = get_queue('default')
    job = rq.get_current_job()
    add_metadata(job, user, menu_item)
    
    job.meta['current_step'] = "Iniciando atualização completa"
    job.save_meta()
    
    try:
        # Executa as tasks em sequência com intervalos menores
        queue.enqueue(update_olt_system_task, user=user, menu_item="Atualização Sistema OLT", job_timeout=300, at_front=False)
        sleep(2)  # Pequena pausa entre enqueue
        queue.enqueue(update_port_occupation_task, user=user, menu_item="Atualização de Portas", job_timeout=1200, at_front=False)
        sleep(2)
        queue.enqueue(update_onus_task, user=user, menu_item="Atualização de ONUs", job_timeout=1200, at_front=False)
        sleep(2)
        queue.enqueue(update_mac_task, user=user, menu_item="Atualização de MAC", job_timeout=1200, at_front=False)
        sleep(2)
        queue.enqueue(update_clientes_task, user=user, menu_item="Atualização de Clientes", job_timeout=1200, at_front=False)
        
        return "Sequência de atualizações completa iniciada"
    
    except Exception as e:
        job.meta['current_step'] = f"Erro: {str(e)}"
        job.save_meta()
        # Fecha conexões em caso de erro
        for conn in connections.all():
            conn.close()
        raise


@django_rq.job('default', timeout=3600)
def scheduled_complete_update_task(user=None, menu_item=None):
    """
    Task ESPECIAL para agendamento automático - NÃO requer autenticação
    Executa atualização completa de TODOS os dados do sistema
    """
    from django.db import connections
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Fecha conexões antes de iniciar
    for conn in connections.all():
        conn.close()
    
    queue = get_queue('default')
    job = rq.get_current_job()
    
    # Adiciona metadados sem verificações de autenticação
    job.meta['user'] = user or 'Sistema Automático'
    job.meta['menu_item'] = menu_item or 'Atualização Periódica Completa'
    job.meta['started_at'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    job.meta['current_step'] = "Iniciando atualização completa automática"
    job.save_meta()
    
    logger.info(f"[SCHEDULER] Iniciando atualização completa automática - User: {job.meta['user']}")
    
    try:
        # Executa as tasks em sequência
        logger.info("[SCHEDULER] → Agendando atualização do sistema OLT...")
        queue.enqueue(update_olt_system_task, user=user, menu_item="Atualização Sistema OLT", job_timeout=300, at_front=False)
        sleep(2)
        
        logger.info("[SCHEDULER] → Agendando atualização de portas...")
        queue.enqueue(update_port_occupation_task, user=user, menu_item="Atualização de Portas", job_timeout=1200, at_front=False)
        sleep(2)
        
        logger.info("[SCHEDULER] → Agendando atualização de ONUs...")
        queue.enqueue(update_onus_task, user=user, menu_item="Atualização de ONUs", job_timeout=1200, at_front=False)
        sleep(2)
        
        logger.info("[SCHEDULER] → Agendando atualização de MACs...")
        queue.enqueue(update_mac_task, user=user, menu_item="Atualização de MAC", job_timeout=1200, at_front=False)
        sleep(2)
        
        logger.info("[SCHEDULER] → Agendando atualização de clientes...")
        queue.enqueue(update_clientes_task, user=user, menu_item="Atualização de Clientes", job_timeout=1200, at_front=False)
        
        job.meta['current_step'] = "Sequência de atualizações completa agendada com sucesso"
        job.save_meta()
        
        logger.info("[SCHEDULER] ✓ Atualização completa automática agendada com sucesso")
        return "Sequência de atualizações automática completa iniciada"
    
    except Exception as e:
        error_msg = f"Erro ao agendar atualização completa: {str(e)}"
        logger.error(f"[SCHEDULER] ✗ {error_msg}")
        job.meta['current_step'] = error_msg
        job.save_meta()
        
        # Fecha conexões em caso de erro
        for conn in connections.all():
            conn.close()
        raise


@django_rq.job
def sincronizar_os_task(limite_paginas=None, user=None, menu_item=None, sync_all=False):
    """Task para sincronizar Ordens de Serviço do IXC
    
    Args:
        limite_paginas: Limite de páginas a processar (None = todas)
        user: Usuário que iniciou a tarefa
        menu_item: Item do menu
        sync_all: Se True, sincroniza todas as OS (ignora limite_paginas)
    """
    from .client_utils import IxcOSClient
    from django.db import connections
    
    job = rq.get_current_job()
    add_metadata(job, user, menu_item or "Sincronização de Ordens de Serviço IXC")
    
    try:
        job.meta['current_step'] = "Iniciando sincronização com IXC"
        job.save_meta()
        
        # Criar cliente IXC
        ixc_client = IxcOSClient()
        
        # Determinar limite de páginas
        if sync_all:
            limite_final = None
            job.meta['current_step'] = "Sincronizando TODAS as OS (sem limite)"
        elif limite_paginas:
            limite_final = limite_paginas
            job.meta['current_step'] = f"Sincronizando até {limite_paginas} páginas de OS"
        else:
            limite_final = None
            job.meta['current_step'] = "Sincronizando todas as OS disponíveis"
        
        job.save_meta()
        
        # Executar sincronização
        sucesso = ixc_client.sincronizar_ordens_servico(limite_paginas=limite_final)
        
        if sucesso:
            job.meta['current_step'] = "Sincronização concluída com sucesso"
            job.save_meta()
            
            if sync_all:
                return "Sincronização COMPLETA de OS concluída - todas as páginas processadas"
            elif limite_final:
                return f"Sincronização de OS concluída - processadas até {limite_final} páginas"
            else:
                return "Sincronização de OS concluída - todas as páginas disponíveis processadas"
        else:
            job.meta['current_step'] = "Erro na sincronização"
            job.save_meta()
            return "Erro na sincronização de OS"
    
    except Exception as e:
        job.meta['current_step'] = f"Erro na sincronização: {str(e)}"
        job.save_meta()
        # Fecha conexões em caso de erro
        for conn in connections.all():
            conn.close()
        raise
