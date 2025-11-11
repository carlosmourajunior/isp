#!/usr/bin/env python3
"""
Serviço de atualização completa agendada
Execute este script para iniciar a atualização automática de TODOS os dados a cada 1 hora
(ONUs, Clientes, Portas, Dados da OLT, etc.)
"""

import os
import sys
import django
import logging

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/code/logs/olt_scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

from django.core.management import call_command

def main():
    """Função principal do serviço"""
    logger = logging.getLogger(__name__)
    
    logger.info("=== Iniciando Serviço de Atualização Completa ===")
    logger.info("Atualização COMPLETA será executada a cada 1 hora")
    logger.info("Inclui: ONUs, Clientes, Portas, Dados OLT, MACs, etc.")
    logger.info("Para parar o serviço, use Ctrl+C")
    
    try:
        # Executar comando de coleta periódica
        call_command('collect_olt_periodic')
    except KeyboardInterrupt:
        logger.info("Serviço interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro no serviço: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()