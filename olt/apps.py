from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class OltConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'olt'

    def ready(self):
        """Código executado quando a aplicação está pronta"""
        try:
            # Importa sinais para gerenciar cache de IPs
            import olt.signals
            
            # Executa tarefas apenas se não estivermos executando migrações
            import sys
            if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
                # Executar tarefas de startup (importar IPs do settings, etc.)
                from .startup import startup_tasks
                startup_tasks()
                
                # Importa e inicia o scheduler
                from .scheduler import start_scheduler
                start_scheduler()
                logger.info("🔄 Scheduler de atualizações automáticas iniciado")
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar aplicação: {e}")
