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
            # Alertas de segurança no Telegram (falhas de login, login de admin)
            import olt.sinais_seguranca  # noqa: F401
            
            # Executa tarefas apenas se não estivermos executando migrações
            import sys
            if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
                # Executar tarefas de startup (importar IPs do settings, etc.)
                from .startup import startup_tasks
                startup_tasks()
                # A atualização automática não sobe mais aqui (subia em todo
                # processo): roda só no container `scheduler`. Ver olt/auto_update.py.
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar aplicação: {e}")
