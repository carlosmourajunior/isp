#!/usr/bin/env python
"""
Script para investigar problemas de persistência de dados.
Detecta conflitos de banco, conexões múltiplas, etc.
"""
import os
import django
import sys
import logging
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from django.db import connections, connection
from django.core.management import call_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_connections():
    """Verifica conexões ativas e conflitos"""
    logger.info("🔍 INVESTIGANDO CONEXÕES DO BANCO")
    logger.info("=" * 40)
    
    try:
        cursor = connection.cursor()
        
        # 1. Verificar informações básicas do banco
        cursor.execute("SELECT version(), current_database(), current_user, inet_server_addr(), inet_server_port()")
        db_info = cursor.fetchone()
        logger.info(f"📊 Banco: {db_info[1]} | Usuário: {db_info[2]} | Servidor: {db_info[3]}:{db_info[4]}")
        
        # 2. Verificar todas as conexões ativas
        cursor.execute("""
            SELECT pid, usename, application_name, client_addr, client_port, 
                   backend_start, state, query_start, query
            FROM pg_stat_activity 
            WHERE datname = current_database()
            ORDER BY backend_start DESC
        """)
        
        connections_info = cursor.fetchall()
        logger.info(f"🔗 Total de conexões ativas: {len(connections_info)}")
        
        for conn in connections_info:
            pid, user, app, addr, port, start, state, query_start, query = conn
            logger.info(f"  PID {pid}: {user}@{addr}:{port} [{app}] - Estado: {state}")
            if query and len(str(query).strip()) > 10:
                query_preview = str(query).strip()[:100].replace('\n', ' ')
                logger.info(f"    Query: {query_preview}...")
        
        # 3. Verificar locks ativos
        cursor.execute("""
            SELECT l.pid, l.mode, l.granted, c.relname as table_name
            FROM pg_locks l
            JOIN pg_class c ON l.relation = c.oid
            WHERE l.relation IS NOT NULL
            ORDER BY l.pid
        """)
        
        locks = cursor.fetchall()
        if locks:
            logger.warning(f"🔒 Locks ativos detectados: {len(locks)}")
            for lock in locks[:10]:  # Limitar a 10 para não poluir
                logger.warning(f"  PID {lock[0]}: {lock[1]} em '{lock[3]}' (Granted: {lock[2]})")
        else:
            logger.info("✅ Nenhum lock ativo detectado")
        
        # 4. Verificar configurações de autocommit e transações
        cursor.execute("SHOW autocommit")
        autocommit = cursor.fetchone()[0]
        logger.info(f"⚙️ Autocommit: {autocommit}")
        
        # 5. Verificar WAL (Write-Ahead Logging)
        cursor.execute("SELECT pg_current_wal_lsn(), pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0')")
        wal_info = cursor.fetchone()
        logger.info(f"📝 WAL atual: {wal_info[0]} (Diff: {wal_info[1]} bytes)")
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar conexões: {e}")

def check_data_consistency():
    """Verifica consistência dos dados"""
    logger.info("\n🔍 VERIFICANDO CONSISTÊNCIA DOS DADOS")
    logger.info("=" * 35)
    
    try:
        cursor = connection.cursor()
        
        # 1. Verificar integridade das tabelas principais
        tables_to_check = [
            'auth_user',
            'django_session', 
            'olt_clientefibraixc',
            'olt_onu',
            'olt_oltusers',
            'olt_oltslot',
            'olt_olttemperature'
        ]
        
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*), MIN(id), MAX(id) FROM {table}")
                count, min_id, max_id = cursor.fetchone()
                
                # Verificar se há gaps nos IDs (pode indicar deletions)
                if min_id and max_id and count > 0:
                    expected_count = max_id - min_id + 1
                    gap_percentage = ((expected_count - count) / expected_count) * 100 if expected_count > 0 else 0
                    
                    if gap_percentage > 10:
                        logger.warning(f"⚠️ {table}: {count} registros, IDs {min_id}-{max_id} (Gap: {gap_percentage:.1f}%)")
                    else:
                        logger.info(f"✅ {table}: {count} registros, IDs {min_id}-{max_id}")
                else:
                    logger.info(f"📊 {table}: {count} registros")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao verificar {table}: {e}")
        
        # 2. Verificar últimas modificações
        cursor.execute("""
            SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, 
                   last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
            FROM pg_stat_user_tables 
            WHERE schemaname = 'public'
            ORDER BY greatest(n_tup_ins, n_tup_upd, n_tup_del) DESC
        """)
        
        table_stats = cursor.fetchall()
        logger.info("\n📊 Estatísticas de modificações (Top 5):")
        for stat in table_stats[:5]:
            schema, table, ins, upd, del_, vacuum, auto_vacuum, analyze, auto_analyze = stat
            logger.info(f"  {table}: +{ins} ~{upd} -{del_} | Vacuum: {vacuum or auto_vacuum or 'Nunca'}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar consistência: {e}")

def check_django_migrations():
    """Verifica estado das migrações Django"""
    logger.info("\n🔍 VERIFICANDO MIGRAÇÕES DJANGO")
    logger.info("=" * 30)
    
    try:
        from django.db.migrations.executor import MigrationExecutor
        executor = MigrationExecutor(connection)
        
        # Verificar migrações não aplicadas
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        
        if plan:
            logger.warning(f"⚠️ {len(plan)} migrações pendentes:")
            for migration, backwards in plan:
                direction = "⬅️ REVERTER" if backwards else "➡️ APLICAR"
                logger.warning(f"  {direction} {migration.app_label}.{migration.name}")
        else:
            logger.info("✅ Todas as migrações estão aplicadas")
        
        # Verificar migrações aplicadas recentemente
        cursor = connection.cursor()
        cursor.execute("""
            SELECT app, name, applied 
            FROM django_migrations 
            ORDER BY applied DESC 
            LIMIT 10
        """)
        
        recent_migrations = cursor.fetchall()
        logger.info("\n📋 Últimas 5 migrações aplicadas:")
        for app, name, applied in recent_migrations[:5]:
            logger.info(f"  {app}.{name} - {applied}")
            
    except Exception as e:
        logger.error(f"❌ Erro ao verificar migrações: {e}")

def check_container_restarts():
    """Simula verificação de restarts dos containers"""
    logger.info("\n🔍 VERIFICANDO RESTARTS DOS CONTAINERS")
    logger.info("=" * 35)
    
    logger.info("💡 Execute no servidor:")
    logger.info("   docker-compose ps")
    logger.info("   docker stats --no-stream")
    logger.info("   docker-compose logs db --tail=50")
    logger.info("   docker inspect isp-db-1 | grep RestartCount")

def check_scheduled_tasks():
    """Verifica se há tarefas agendadas problemáticas"""
    logger.info("\n🔍 VERIFICANDO TAREFAS AGENDADAS")
    logger.info("=" * 30)
    
    try:
        # Verificar jobs do RQ
        from django_rq import get_queue
        from rq.job import Job
        
        queue = get_queue('default')
        
        # Jobs em execução
        started_jobs = queue.started_job_registry
        logger.info(f"🔄 Jobs em execução: {len(started_jobs)}")
        
        # Jobs falhados
        failed_jobs = queue.failed_job_registry
        logger.info(f"❌ Jobs falhados: {len(failed_jobs)}")
        
        if len(failed_jobs) > 0:
            logger.warning("⚠️ Jobs falhados recentes:")
            for job_id in list(failed_jobs.get_job_ids())[-5:]:  # Últimos 5
                try:
                    job = Job.fetch(job_id, connection=queue.connection)
                    logger.warning(f"  {job_id}: {job.func_name} - {job.exc_info}")
                except:
                    logger.warning(f"  {job_id}: Não foi possível carregar detalhes")
        
        # Jobs agendados
        scheduled_jobs = queue.scheduled_job_registry
        logger.info(f"⏰ Jobs agendados: {len(scheduled_jobs)}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar tarefas: {e}")

def main():
    """Função principal de investigação"""
    logger.info("🕵️ INVESTIGAÇÃO DE PERDA DE DADOS")
    logger.info("=" * 35)
    logger.info(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    check_database_connections()
    check_data_consistency() 
    check_django_migrations()
    check_scheduled_tasks()
    check_container_restarts()
    
    logger.info("\n📋 PRÓXIMOS PASSOS RECOMENDADOS:")
    logger.info("1. Execute os comandos Docker sugeridos acima")
    logger.info("2. Monitore logs em tempo real: docker-compose logs -f db web")
    logger.info("3. Verifique cron jobs do sistema: crontab -l")
    logger.info("4. Monitore uso de memória: docker stats")

if __name__ == "__main__":
    main()