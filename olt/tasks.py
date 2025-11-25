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
    Executa atualização completa de TODOS os dados do sistema DIRETAMENTE
    """
    from django.db import connections
    import logging
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
    
    logger = logging.getLogger(__name__)
    
    # Fecha conexões antes de iniciar
    for conn in connections.all():
        try:
            conn.close()
        except:
            pass
    
    job = rq.get_current_job()
    
    # Adiciona metadados sem verificações de autenticação
    if job:
        job.meta['user'] = user or 'Sistema Automático'
        job.meta['menu_item'] = menu_item or 'Atualização Periódica Completa'
        job.meta['started_at'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        job.meta['current_step'] = "Iniciando atualização completa automática"
        job.save_meta()
    
    logger.info(f"[SCHEDULER] Iniciando atualização completa automática")
    
    resultados = {
        'olt_system': {'status': False, 'error': None},
        'port_occupation': {'status': False, 'error': None},
        'onus': {'status': False, 'error': None},
        'macs': {'status': False, 'error': None},
        'clientes': {'status': False, 'error': None}
    }
    
    def run_with_timeout(func, timeout_seconds, *args, **kwargs):
        """Executa função com timeout usando ThreadPoolExecutor"""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=timeout_seconds)
            except FutureTimeoutError:
                future.cancel()
                raise TimeoutError(f"Operação excedeu {timeout_seconds}s")
    
    # 1. Atualizar Sistema OLT
    try:
        if job:
            job.meta['current_step'] = "Atualizando Sistema OLT..."
            job.save_meta()
        
        logger.info("[SCHEDULER] → Atualizando Sistema OLT...")
        
        def update_olt_system():
            collector = OltSystemCollector()
            return collector.collect_all_system_data()
        
        result = run_with_timeout(update_olt_system, 300)  # 5 minutos
        resultados['olt_system']['status'] = result is not None
        logger.info(f"[SCHEDULER] ✓ Sistema OLT: {'Sucesso' if resultados['olt_system']['status'] else 'Falha'}")
            
    except TimeoutError as e:
        error_msg = str(e)
        logger.error(f"[SCHEDULER] ✗ Timeout: {error_msg}")
        resultados['olt_system']['error'] = error_msg
    except Exception as e:
        error_msg = f"Erro no Sistema OLT: {str(e)}"
        logger.error(f"[SCHEDULER] ✗ {error_msg}")
        resultados['olt_system']['error'] = error_msg
    
    # 2. Atualizar Ocupação de Portas
    try:
        if job:
            job.meta['current_step'] = "Atualizando Ocupação de Portas..."
            job.save_meta()
        
        logger.info("[SCHEDULER] → Atualizando Ocupação de Portas...")
        
        def update_ports():
            connector = olt_connector()
            connector.update_port_ocupation(read_timeout=600, expect_string='typ:isadmin>#')
            return True
        
        run_with_timeout(update_ports, 600)  # 10 minutos
        resultados['port_occupation']['status'] = True
        logger.info("[SCHEDULER] ✓ Ocupação de Portas: Sucesso")
            
    except TimeoutError as e:
        error_msg = str(e)
        logger.error(f"[SCHEDULER] ✗ Timeout: {error_msg}")
        resultados['port_occupation']['error'] = error_msg
    except Exception as e:
        error_msg = f"Erro em Ocupação de Portas: {str(e)}"
        logger.error(f"[SCHEDULER] ✗ {error_msg}")
        resultados['port_occupation']['error'] = error_msg
    
    # 3. Atualizar ONUs
    try:
        if job:
            job.meta['current_step'] = "Atualizando ONUs..."
            job.save_meta()
        
        logger.info("[SCHEDULER] → Atualizando ONUs...")
        
        def update_onus():
            connector = olt_connector()
            connector.update_all_ports()
            return True
        
        run_with_timeout(update_onus, 900)  # 15 minutos
        resultados['onus']['status'] = True
        logger.info("[SCHEDULER] ✓ ONUs: Sucesso")
            
    except TimeoutError as e:
        error_msg = str(e)
        logger.error(f"[SCHEDULER] ✗ Timeout: {error_msg}")
        resultados['onus']['error'] = error_msg
    except Exception as e:
        error_msg = f"Erro em ONUs: {str(e)}"
        logger.error(f"[SCHEDULER] ✗ {error_msg}")
        resultados['onus']['error'] = error_msg
    
    # 4. Atualizar MACs
    try:
        if job:
            job.meta['current_step'] = "Atualizando MACs..."
            job.save_meta()
        
        logger.info("[SCHEDULER] → Atualizando MACs...")
        
        def update_macs():
            connector = olt_connector()
            connector.get_mac_values()
            return True
        
        run_with_timeout(update_macs, 600)  # 10 minutos
        resultados['macs']['status'] = True
        logger.info("[SCHEDULER] ✓ MACs: Sucesso")
            
    except TimeoutError as e:
        error_msg = str(e)
        logger.error(f"[SCHEDULER] ✗ Timeout: {error_msg}")
        resultados['macs']['error'] = error_msg
    except Exception as e:
        error_msg = f"Erro em MACs: {str(e)}"
        logger.error(f"[SCHEDULER] ✗ {error_msg}")
        resultados['macs']['error'] = error_msg
    
    # 5. Atualizar Clientes
    try:
        if job:
            job.meta['current_step'] = "Atualizando Clientes Fibra..."
            job.save_meta()
        
        logger.info("[SCHEDULER] → Atualizando Clientes Fibra...")
        
        def update_clients():
            update_clientes()
            return True
        
        run_with_timeout(update_clients, 300)  # 5 minutos
        resultados['clientes']['status'] = True
        logger.info("[SCHEDULER] ✓ Clientes Fibra: Sucesso")
            
    except TimeoutError as e:
        error_msg = str(e)
        logger.error(f"[SCHEDULER] ✗ Timeout: {error_msg}")
        resultados['clientes']['error'] = error_msg
    except Exception as e:
        error_msg = f"Erro em Clientes: {str(e)}"
        logger.error(f"[SCHEDULER] ✗ {error_msg}")
        resultados['clientes']['error'] = error_msg
    
    # Resumo final
    sucessos = sum(1 for v in resultados.values() if v['status'])
    total = len(resultados)
    
    if job:
        job.meta['current_step'] = f"Atualização completa finalizada: {sucessos}/{total} sucessos"
        job.meta['resultados'] = resultados
        job.save_meta()
    
    logger.info(f"[SCHEDULER] ✓ Atualização completa automática finalizada: {sucessos}/{total} sucessos")
    for nome, resultado in resultados.items():
        status_emoji = "✅" if resultado['status'] else "❌"
        error_info = f" - {resultado['error']}" if resultado['error'] else ""
        logger.info(f"[SCHEDULER]   {status_emoji} {nome}: {'OK' if resultado['status'] else 'FALHOU'}{error_info}")
    
    # Sempre fecha conexões ao final
    for conn in connections.all():
        try:
            conn.close()
        except:
            pass
    
    return f"Atualização automática completa: {sucessos}/{total} sucessos"


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
