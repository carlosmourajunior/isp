#!/usr/bin/env python
"""
Script para verificar e corrigir problemas comuns do banco de dados.
Use este script quando houver problemas de "relation does not exist".
"""
import os
import django
import sys
from django.core.management import execute_from_command_line

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from django.db import connections, transaction
from django.core.management import call_command
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_connection():
    """Verifica se a conexão com o banco está funcionando"""
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        logger.info("✅ Conexão com o banco de dados OK")
        return True
    except Exception as e:
        logger.error(f"❌ Erro na conexão com o banco: {e}")
        return False

def check_tables_exist():
    """Verifica se as tabelas principais existem"""
    try:
        from django.db import connection
        cursor = connection.cursor()
        
        # Verifica tabelas essenciais do Django
        essential_tables = [
            'django_session',
            'django_content_type',
            'auth_user',
            'django_migrations'
        ]
        
        missing_tables = []
        for table in essential_tables:
            cursor.execute(f"SELECT to_regclass('{table}')")
            result = cursor.fetchone()
            if result[0] is None:
                missing_tables.append(table)
                logger.warning(f"⚠️  Tabela ausente: {table}")
            else:
                logger.info(f"✅ Tabela existe: {table}")
        
        return len(missing_tables) == 0, missing_tables
    
    except Exception as e:
        logger.error(f"❌ Erro ao verificar tabelas: {e}")
        return False, []

def force_close_connections():
    """Força o fechamento de todas as conexões do Django"""
    try:
        for conn in connections.all():
            conn.close()
        logger.info("✅ Conexões fechadas")
    except Exception as e:
        logger.error(f"❌ Erro ao fechar conexões: {e}")

def run_migrations():
    """Executa as migrações do Django"""
    try:
        logger.info("🔄 Executando migrações...")
        call_command('migrate', verbosity=2)
        logger.info("✅ Migrações executadas")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao executar migrações: {e}")
        return False

def create_superuser_if_needed():
    """Cria um superusuário se não existir"""
    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(is_superuser=True).exists():
            logger.info("🔄 Criando superusuário...")
            call_command('createsuperuser', '--noinput', 
                        username='admin', email='admin@localhost')
            logger.info("✅ Superusuário criado")
        else:
            logger.info("✅ Superusuário já existe")
    except Exception as e:
        logger.error(f"❌ Erro ao criar superusuário: {e}")

def fix_database():
    """Executa a sequência de correções"""
    logger.info("🔧 Iniciando correção do banco de dados...")
    
    # 1. Fechar conexões
    force_close_connections()
    
    # 2. Verificar conexão
    if not check_database_connection():
        logger.error("❌ Não foi possível conectar ao banco")
        return False
    
    # 3. Verificar tabelas
    tables_ok, missing = check_tables_exist()
    
    if not tables_ok:
        logger.warning(f"⚠️  Tabelas ausentes detectadas: {missing}")
        
        # 4. Executar migrações
        if not run_migrations():
            logger.error("❌ Falha ao executar migrações")
            return False
        
        # 5. Verificar novamente
        tables_ok, missing = check_tables_exist()
        if not tables_ok:
            logger.error(f"❌ Ainda há tabelas ausentes: {missing}")
            return False
    
    # 6. Criar superusuário se necessário
    create_superuser_if_needed()
    
    logger.info("✅ Correção do banco concluída!")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Apenas verificar, não corrigir
        logger.info("🔍 Verificando banco de dados...")
        check_database_connection()
        check_tables_exist()
    else:
        # Executar correção completa
        fix_database()