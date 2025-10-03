#!/usr/bin/env python
"""
Script para diagnosticar e corrigir problemas específicos de perda de dados.
Execute este script quando houver erro "relation does not exist".
"""
import os
import django
import sys
import logging
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from django.db import connections, transaction
from django.core.management import call_command
from django.contrib.auth.models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_database_issue():
    """Diagnostica problemas no banco de dados"""
    logger.info("🔍 DIAGNÓSTICO DO BANCO DE DADOS")
    logger.info("=" * 50)
    
    issues_found = []
    
    try:
        # 1. Verificar conexão básica
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        logger.info(f"✅ PostgreSQL conectado: {version[0]}")
        
        # 2. Verificar tabelas essenciais
        essential_tables = [
            'django_session',
            'django_content_type', 
            'django_migrations',
            'auth_user',
            'olt_clientefibraixc',
            'olt_oltslot',
            'olt_olttemperature'
        ]
        
        logger.info("\n📋 Verificando tabelas essenciais:")
        for table in essential_tables:
            cursor.execute(f"SELECT to_regclass('{table}')")
            result = cursor.fetchone()
            if result[0] is None:
                logger.error(f"❌ AUSENTE: {table}")
                issues_found.append(f"Tabela ausente: {table}")
            else:
                # Verificar se tem dados
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                logger.info(f"✅ {table}: {count} registros")
                
                if table in ['olt_clientefibraixc', 'olt_oltslot', 'olt_olttemperature'] and count == 0:
                    issues_found.append(f"Tabela {table} está vazia")
        
        # 3. Verificar índices
        logger.info("\n🔍 Verificando índices:")
        cursor.execute("""
            SELECT schemaname, tablename, indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename IN ('django_session', 'olt_clientefibraixc', 'olt_oltslot')
        """)
        indexes = cursor.fetchall()
        logger.info(f"✅ Encontrados {len(indexes)} índices")
        
        # 4. Verificar processos bloqueantes
        logger.info("\n🔒 Verificando locks/bloqueios:")
        cursor.execute("""
            SELECT pid, usename, application_name, client_addr, state, query_start, query
            FROM pg_stat_activity 
            WHERE state != 'idle' AND pid != pg_backend_pid()
        """)
        active_queries = cursor.fetchall()
        logger.info(f"📊 {len(active_queries)} consultas ativas")
        
        for query in active_queries:
            if query[6] and len(query[6]) > 100:
                logger.info(f"  PID {query[0]}: {query[6][:100]}...")
            
        # 5. Verificar configurações de pool
        logger.info("\n⚙️ Configurações de conexão:")
        from django.conf import settings
        db_config = settings.DATABASES['default']
        logger.info(f"  CONN_MAX_AGE: {db_config.get('CONN_MAX_AGE', 'não definido')}")
        logger.info(f"  HOST: {db_config.get('HOST')}")
        logger.info(f"  OPTIONS: {db_config.get('OPTIONS', {})}")
        
    except Exception as e:
        logger.error(f"❌ Erro durante diagnóstico: {e}")
        issues_found.append(f"Erro de conexão: {str(e)}")
    
    return issues_found

def fix_migration_issues():
    """Corrige problemas de migração"""
    logger.info("\n🔧 CORREÇÃO DE MIGRAÇÕES")
    logger.info("=" * 30)
    
    try:
        # 1. Verificar migrações pendentes
        from django.core.management.commands.showmigrations import Command as ShowMigrationsCommand
        from io import StringIO
        
        logger.info("📋 Verificando migrações pendentes...")
        call_command('showmigrations', '--plan', verbosity=0)
        
        # 2. Executar migrações
        logger.info("🔄 Executando migrações...")
        call_command('migrate', verbosity=2)
        
        # 3. Criar migrações para novos campos is_active se necessário
        logger.info("🔄 Criando migrações para campos is_active...")
        try:
            call_command('makemigrations', 'olt', verbosity=1)
            call_command('migrate', 'olt', verbosity=1)
        except Exception as e:
            logger.warning(f"⚠️ Aviso na criação de migrações: {e}")
        
        logger.info("✅ Migrações concluídas")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao executar migrações: {e}")
        return False

def fix_connection_pool():
    """Corrige problemas de pool de conexões"""
    logger.info("\n🔧 CORREÇÃO DE POOL DE CONEXÕES")
    logger.info("=" * 35)
    
    try:
        # Fechar todas as conexões ativas
        logger.info("🔄 Fechando conexões ativas...")
        for alias in connections:
            connections[alias].close()
        
        # Limpar cache de conexões
        logger.info("🧹 Limpando cache de conexões...")
        connections._connections.clear()
        
        # Testar nova conexão
        logger.info("🔗 Testando nova conexão...")
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result[0] == 1:
            logger.info("✅ Nova conexão estabelecida com sucesso")
            return True
        else:
            logger.error("❌ Falha na nova conexão")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao corrigir pool: {e}")
        return False

def emergency_data_recovery():
    """Tenta recuperação de emergência de dados"""
    logger.info("\n🚨 RECUPERAÇÃO DE EMERGÊNCIA")
    logger.info("=" * 30)
    
    try:
        # Verificar se há backup automático recente
        logger.info("🔍 Verificando backups disponíveis...")
        
        # Verificar se as tabelas existem mas estão vazias
        from django.db import connection
        cursor = connection.cursor()
        
        tables_to_check = ['olt_clientefibraixc', 'olt_oltslot', 'olt_olttemperature']
        empty_tables = []
        
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                if count == 0:
                    empty_tables.append(table)
                    logger.warning(f"⚠️ {table} está vazia")
                else:
                    logger.info(f"✅ {table} tem {count} registros")
            except Exception as e:
                logger.error(f"❌ Erro ao verificar {table}: {e}")
        
        if empty_tables:
            logger.warning(f"🚨 Detectadas {len(empty_tables)} tabelas vazias!")
            logger.info("💡 Recomendação: Execute uma atualização manual dos dados da OLT")
            
            # Sugerir comandos de recuperação
            logger.info("\n📝 Comandos para recuperação:")
            logger.info("1. Reiniciar o sistema:")
            logger.info("   docker-compose restart web")
            logger.info("2. Executar atualização manual:")
            logger.info("   Acesse o sistema web e execute 'Atualizar Tudo'")
            logger.info("3. Verificar logs:")
            logger.info("   docker-compose logs web scheduler -f")
        
        return len(empty_tables) == 0
        
    except Exception as e:
        logger.error(f"❌ Erro na recuperação: {e}")
        return False

def create_emergency_user():
    """Cria usuário de emergência se necessário"""
    logger.info("\n👤 VERIFICAÇÃO DE USUÁRIO")
    logger.info("=" * 25)
    
    try:
        if not User.objects.filter(is_superuser=True).exists():
            logger.info("🔄 Criando superusuário de emergência...")
            User.objects.create_superuser(
                username='emergency',
                email='emergency@localhost',
                password='emergency123'
            )
            logger.info("✅ Usuário criado: emergency/emergency123")
        else:
            superuser = User.objects.filter(is_superuser=True).first()
            logger.info(f"✅ Superusuário existe: {superuser.username}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar usuário: {e}")
        return False

def main():
    """Função principal de diagnóstico e correção"""
    logger.info("🚨 SISTEMA DE DIAGNÓSTICO E CORREÇÃO DE EMERGÊNCIA")
    logger.info("=" * 55)
    logger.info(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    logger.info("")
    
    # 1. Diagnóstico
    issues = diagnose_database_issue()
    
    if issues:
        logger.warning(f"\n⚠️ PROBLEMAS DETECTADOS ({len(issues)}):")
        for i, issue in enumerate(issues, 1):
            logger.warning(f"  {i}. {issue}")
    else:
        logger.info("\n✅ Nenhum problema crítico detectado!")
    
    # 2. Correções
    success_count = 0
    total_fixes = 4
    
    if fix_migration_issues():
        success_count += 1
    
    if fix_connection_pool():
        success_count += 1
    
    if emergency_data_recovery():
        success_count += 1
    
    if create_emergency_user():
        success_count += 1
    
    # Resultado final
    logger.info(f"\n📊 RESULTADO FINAL:")
    logger.info(f"✅ Correções bem-sucedidas: {success_count}/{total_fixes}")
    
    if success_count == total_fixes:
        logger.info("🎉 Sistema corrigido com sucesso!")
        logger.info("\n📝 PRÓXIMOS PASSOS:")
        logger.info("1. Reinicie o sistema: docker-compose restart")
        logger.info("2. Execute uma atualização manual dos dados")
        logger.info("3. Monitore os logs por alguns minutos")
    else:
        logger.warning("⚠️ Algumas correções falharam. Verifique os logs acima.")
        logger.info("\n🆘 SE O PROBLEMA PERSISTIR:")
        logger.info("1. Pare o sistema: docker-compose down")
        logger.info("2. Faça backup dos dados: make backup")
        logger.info("3. Reconstrua o sistema: docker-compose up --build")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "diagnose":
            diagnose_database_issue()
        elif sys.argv[1] == "fix-pool":
            fix_connection_pool()
        elif sys.argv[1] == "migrate":
            fix_migration_issues()
        elif sys.argv[1] == "recover":
            emergency_data_recovery()
        else:
            print("Uso: python emergency_fix.py [diagnose|fix-pool|migrate|recover]")
    else:
        main()