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
            
            # Importa e inicia o scheduler apenas se não estivermos executando migrações
            import sys
            if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
                from .scheduler import start_scheduler
                start_scheduler()
                logger.info("🔄 Scheduler de atualizações automáticas iniciado")
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar scheduler automático: {e}")
