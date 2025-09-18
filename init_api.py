#!/usr/bin/env python3
"""
Script de inicialização da API
Este script executa as migrações e cria um superusuário se necessário
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

def init_django():
    """Inicializa o Django"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'olt_connector.settings')
    django.setup()

def run_migrations():
    """Executa as migrações do banco de dados"""
    print("🔄 Executando migrações...")
    execute_from_command_line(['manage.py', 'migrate'])
    print("✅ Migrações concluídas!")

def create_superuser():
    """Cria um superusuário se não existir"""
    from django.contrib.auth.models import User
    
    username = 'admin'
    email = 'admin@localhost'
    password = 'admin123'
    
    if not User.objects.filter(username=username).exists():
        print(f"🔄 Criando superusuário '{username}'...")
        User.objects.create_superuser(username, email, password)
        print(f"✅ Superusuário '{username}' criado com sucesso!")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print("   ⚠️  Altere a senha em produção!")
    else:
        print(f"ℹ️  Superusuário '{username}' já existe")

def main():
    """Função principal"""
    print("🚀 Inicializando API OLT/ONT...")
    print("=" * 50)
    
    try:
        init_django()
        run_migrations()
        create_superuser()
        
        print("\n🎉 Inicialização concluída com sucesso!")
        print("\nPara testar a API:")
        print("1. Acesse: http://localhost:8000/api/auth/login/")
        print("2. Use as credenciais: admin / admin123")
        print("3. Execute: python test_api.py")
        
    except Exception as e:
        print(f"❌ Erro durante a inicialização: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()