#!/usr/bin/env python
"""
Script para configurar e inicializar as atualizações automáticas.
Execute este script após subir os containers para a primeira vez.
"""
import os
import sys
import django
from pathlib import Path

# Adiciona o diretório do projeto ao Python path
project_path = Path(__file__).parent
if str(project_path) not in sys.path:
    sys.path.append(str(project_path))

# Configura o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()


def setup_auto_updates():
    """Configura as atualizações automáticas"""
    print("🔧 Configurando atualizações automáticas...")
    
    try:
        # Executa migrações
        print("📦 Executando migrações...")
        os.system('python manage.py migrate')
        
        # Inicia o scheduler
        print("⏰ Iniciando scheduler...")
        os.system('python manage.py setup_auto_updates --start')
        
        print("\n✅ Configuração concluída!")
        print("\n📋 Para verificar status:")
        print("   docker-compose exec web python manage.py setup_auto_updates --status")
        print("\n🌐 Para acessar o painel de status:")
        print("   http://localhost:8000/scheduler-status/")
        print("\n📊 Para acessar o dashboard do RQ:")
        print("   http://localhost:8000/django-rq/")
        print("\n🔄 As atualizações automáticas executarão a cada hora (minuto 0)")
        
    except Exception as e:
        print(f"❌ Erro durante a configuração: {e}")
        sys.exit(1)


if __name__ == '__main__':
    setup_auto_updates()