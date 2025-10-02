#!/usr/bin/env python
"""
Script para executar o scheduler de tarefas automáticas.
"""
import os
import django
import time
import logging
import signal
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.scheduler import start_scheduler, stop_scheduler

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def signal_handler(signum, frame):
    """Handler para sinais de sistema"""
    logger.info("🛑 Recebido sinal de parada, finalizando scheduler...")
    stop_scheduler()
    sys.exit(0)

def main():
    """Função principal"""
    # Configurar handlers de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("🔄 Iniciando scheduler de tarefas automáticas...")
        start_scheduler()
        logger.info("✅ Scheduler iniciado! Mantendo processo ativo...")
        
        # Manter o processo rodando
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("🛑 Scheduler interrompido pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro no scheduler: {e}")
    finally:
        stop_scheduler()
        logger.info("✅ Scheduler finalizado")

if __name__ == "__main__":
    main()