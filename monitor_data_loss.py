#!/usr/bin/env python
"""
Monitor contínuo para detectar quando os dados desaparecem.
Execute este script em background para capturar o momento exato.
"""
import os
import django
import time
import logging
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/code/logs/data_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_critical_tables():
    """Verifica tabelas críticas e retorna contadores"""
    try:
        cursor = connection.cursor()
        
        tables_count = {}
        
        # Tabelas críticas para monitorar
        critical_tables = [
            'auth_user',
            'django_session',
            'olt_clientefibraixc', 
            'olt_onu',
            'olt_oltusers'
        ]
        
        for table in critical_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                tables_count[table] = count
            except Exception as e:
                tables_count[table] = f"ERROR: {e}"
        
        return tables_count
        
    except Exception as e:
        logger.error(f"Erro ao verificar tabelas: {e}")
        return {}

def check_active_connections():
    """Verifica conexões ativas que podem estar causando problemas"""
    try:
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as total_connections,
                   COUNT(*) FILTER (WHERE state = 'active') as active_queries,
                   COUNT(*) FILTER (WHERE application_name LIKE '%django%') as django_connections,
                   COUNT(*) FILTER (WHERE application_name LIKE '%rq%') as rq_connections
            FROM pg_stat_activity 
            WHERE datname = current_database()
        """)
        
        result = cursor.fetchone()
        return {
            'total': result[0],
            'active': result[1], 
            'django': result[2],
            'rq': result[3]
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar conexões: {e}")
        return {}

def detect_dangerous_queries():
    """Detecta queries perigosas em execução"""
    try:
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT pid, usename, application_name, state, query_start, query
            FROM pg_stat_activity 
            WHERE datname = current_database()
            AND state = 'active'
            AND (
                query ILIKE '%DELETE%' OR 
                query ILIKE '%DROP%' OR 
                query ILIKE '%TRUNCATE%' OR
                query ILIKE '%ALTER%'
            )
            AND pid != pg_backend_pid()
        """)
        
        dangerous_queries = cursor.fetchall()
        return dangerous_queries
        
    except Exception as e:
        logger.error(f"Erro ao detectar queries perigosas: {e}")
        return []

def monitor_data_integrity():
    """Monitor principal que roda continuamente"""
    logger.info("🔍 INICIANDO MONITOR DE INTEGRIDADE DE DADOS")
    logger.info("=" * 50)
    
    # Estado inicial
    last_counts = check_critical_tables()
    logger.info("📊 Estado inicial das tabelas:")
    for table, count in last_counts.items():
        logger.info(f"  {table}: {count}")
    
    iteration = 0
    alerts_sent = 0
    
    while True:
        try:
            iteration += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Verificar a cada 30 segundos
            if iteration % 6 == 0:  # Log status a cada 3 minutos (6 * 30s)
                logger.info(f"⏰ Monitor ativo - {current_time}")
            
            # Verificar contadores atuais
            current_counts = check_critical_tables()
            
            # Detectar mudanças suspeitas
            for table, current_count in current_counts.items():
                if table in last_counts:
                    last_count = last_counts[table]
                    
                    # Se for erro, pular comparação
                    if isinstance(current_count, str) or isinstance(last_count, str):
                        continue
                    
                    # Detectar perda massiva de dados (mais de 50% ou tabela zerada)
                    if current_count == 0 and last_count > 0:
                        logger.error(f"🚨 ALERTA CRÍTICO: {table} foi COMPLETAMENTE ESVAZIADA!")
                        logger.error(f"   Antes: {last_count} registros | Agora: {current_count}")
                        alerts_sent += 1
                        
                        # Investigar o que aconteceu
                        dangerous = detect_dangerous_queries()
                        if dangerous:
                            logger.error("🔍 Queries perigosas detectadas:")
                            for query in dangerous:
                                logger.error(f"  PID {query[0]} ({query[1]}): {query[5][:200]}...")
                        
                        connections_info = check_active_connections()
                        logger.error(f"🔗 Conexões ativas: {connections_info}")
                        
                    elif last_count > 0 and current_count < (last_count * 0.5):
                        logger.warning(f"⚠️ PERDA SIGNIFICATIVA: {table}")
                        logger.warning(f"   Antes: {last_count} | Agora: {current_count} ({((last_count-current_count)/last_count)*100:.1f}% perdido)")
                        
                    elif current_count > last_count:
                        # Dados foram adicionados - normal
                        if iteration % 30 == 0:  # Log apenas ocasionalmente
                            logger.info(f"✅ {table}: {last_count} → {current_count} (+{current_count-last_count})")
            
            # Atualizar estado
            last_counts = current_counts
            
            # Verificar queries perigosas periodicamente
            if iteration % 20 == 0:  # A cada 10 minutos
                dangerous = detect_dangerous_queries()
                if dangerous:
                    logger.warning(f"⚠️ {len(dangerous)} queries perigosas em execução:")
                    for query in dangerous[:3]:  # Mostrar apenas as 3 primeiras
                        logger.warning(f"  PID {query[0]}: {query[5][:100]}...")
            
            # Verificar se muitos alertas foram enviados (possível loop)
            if alerts_sent > 10:
                logger.error("🛑 Muitos alertas enviados - pausando monitor por 5 minutos")
                time.sleep(300)  # 5 minutos
                alerts_sent = 0
            
            time.sleep(30)  # Verificar a cada 30 segundos
            
        except KeyboardInterrupt:
            logger.info("🛑 Monitor interrompido pelo usuário")
            break
        except Exception as e:
            logger.error(f"❌ Erro no monitor: {e}")
            time.sleep(60)  # Esperar 1 minuto antes de tentar novamente

if __name__ == "__main__":
    monitor_data_integrity()