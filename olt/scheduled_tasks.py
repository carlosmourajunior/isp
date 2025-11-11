"""
Tasks para coleta agendada de dados da OLT
"""
import logging
from datetime import datetime
from olt.utils import OltSystemCollector

logger = logging.getLogger(__name__)

def collect_olt_system_data():
    """
    Task para coletar dados do sistema OLT periodicamente
    Chamada automaticamente a cada 1 hora
    """
    try:
        logger.info("Iniciando coleta agendada de dados da OLT...")
        
        collector = OltSystemCollector()
        result = collector.collect_all_system_data()
        
        if result:
            logger.info(f"Coleta concluída com sucesso: CPU {result.get('cpu_percent')}%, Memória {result.get('mem_percent')}%")
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'data': {
                    'cpu_percent': result.get('cpu_percent'),
                    'mem_percent': result.get('mem_percent'),
                    'model': result.get('model')
                }
            }
        else:
            logger.error("Falha na coleta de dados da OLT")
            return {'success': False, 'error': 'Coleta retornou dados vazios'}
            
    except Exception as e:
        logger.error(f"Erro na coleta agendada da OLT: {str(e)}")
        return {'success': False, 'error': str(e)}

def schedule_periodic_collection():
    """
    Configura a coleta periódica de dados da OLT
    Executa a cada 1 hora
    """
    try:
        import django_rq
        from rq_scheduler import Scheduler
        from datetime import timedelta
        
        # Usar o scheduler do django-rq
        scheduler = Scheduler(connection=django_rq.get_connection())
        
        # Cancelar jobs existentes para evitar duplicatas
        for job in scheduler.get_jobs():
            if job.func_name == 'olt.scheduled_tasks.collect_olt_system_data':
                job.cancel()
        
        # Agendar nova execução a cada 1 hora
        scheduler.schedule(
            scheduled_time=datetime.now(),
            func=collect_olt_system_data,
            interval=timedelta(hours=1),
            repeat=None  # Repetir indefinidamente
        )
        
        logger.info("Coleta periódica da OLT agendada para executar a cada 1 hora")
        return {'success': True, 'message': 'Agendamento configurado com sucesso'}
        
    except Exception as e:
        logger.error(f"Erro ao configurar agendamento: {str(e)}")
        return {'success': False, 'error': str(e)}