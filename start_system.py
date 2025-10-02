#!/usr/bin/env python3
"""
Script de inicialização completo do Sistema ISP
Inclui aplicação principal + monitoramento
"""

import os
import sys
import subprocess
import time
import json
import shutil
from pathlib import Path

class Colors:
    """Cores para output no terminal"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(message, color=Colors.GREEN):
    """Imprimir mensagem colorida"""
    print(f"{color}{message}{Colors.ENDC}")

def print_header(message):
    """Imprimir cabeçalho"""
    print_colored(f"\n{'='*60}", Colors.BLUE)
    print_colored(f"  {message}", Colors.BOLD + Colors.BLUE)
    print_colored(f"{'='*60}", Colors.BLUE)

def check_requirements():
    """Verificar pré-requisitos do sistema"""
    print_header("🔍 VERIFICANDO PRÉ-REQUISITOS")
    
    requirements = []
    
    # Verificar Docker
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_colored(f"✓ Docker: {result.stdout.strip()}")
        else:
            requirements.append("Docker não está instalado")
    except FileNotFoundError:
        requirements.append("Docker não encontrado")
    
    # Verificar Docker Compose
    try:
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print_colored(f"✓ Docker Compose: {result.stdout.strip()}")
        else:
            requirements.append("Docker Compose não está instalado")
    except FileNotFoundError:
        requirements.append("Docker Compose não encontrado")
    
    # Verificar Python
    try:
        version = sys.version.split()[0]
        print_colored(f"✓ Python: {version}")
        if version < "3.8":
            requirements.append("Python 3.8+ é necessário")
    except:
        requirements.append("Python não encontrado")
    
    # Verificar se Docker está rodando
    try:
        result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
        if result.returncode == 0:
            print_colored("✓ Docker daemon está rodando")
        else:
            requirements.append("Docker daemon não está rodando")
    except:
        requirements.append("Não foi possível verificar o Docker daemon")
    
    if requirements:
        print_colored("\n❌ REQUISITOS NÃO ATENDIDOS:", Colors.FAIL)
        for req in requirements:
            print_colored(f"  - {req}", Colors.FAIL)
        return False
    
    print_colored("\n✅ Todos os pré-requisitos atendidos!", Colors.GREEN)
    return True

def create_directories():
    """Criar diretórios necessários"""
    print_header("📁 CRIANDO DIRETÓRIOS")
    
    directories = [
        'data',
        'data/logs',
        'data/postgres',
        'data/redis',
        'data/media',
        'data/staticfiles',
        'logs',
        'monitoring',
        'monitoring/prometheus',
        'monitoring/prometheus/rules',
        'monitoring/grafana',
        'monitoring/grafana/provisioning',
        'monitoring/grafana/provisioning/datasources',
        'monitoring/grafana/provisioning/dashboards',
        'monitoring/grafana/dashboards',
        'monitoring/alertmanager'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print_colored(f"✓ {directory}")
    
    print_colored("\n✅ Diretórios criados com sucesso!")

def check_env_file():
    """Verificar e criar arquivo .env se necessário"""
    print_header("⚙️  VERIFICANDO CONFIGURAÇÕES")
    
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists():
        if env_example.exists():
            shutil.copy('.env.example', '.env')
            print_colored("✓ Arquivo .env criado a partir do .env.example")
        else:
            # Criar .env básico
            env_content = """
# Django Settings
SECRET_KEY=change-this-secret-key-in-production
DEBUG=True
ALLOWED_HOSTS=*

# Database Settings
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# Redis Settings
REDIS_URL=redis://redis:6379/0

# Email Settings (configurar para alertas)
EMAIL_HOST=localhost
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
"""
            with open('.env', 'w') as f:
                f.write(env_content.strip())
            print_colored("✓ Arquivo .env básico criado")
            print_colored("⚠️  Configure as variáveis de ambiente em .env conforme necessário", Colors.WARNING)
    else:
        print_colored("✓ Arquivo .env já existe")

def setup_monitoring_configs():
    """Configurar arquivos de monitoramento se não existirem"""
    print_header("📊 CONFIGURANDO MONITORAMENTO")
    
    configs = {
        'monitoring/prometheus/prometheus.yml': '''global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'django-app'
    static_configs:
      - targets: ['web:8000']
    metrics_path: '/api/metrics'
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']''',
      
        'monitoring/grafana/provisioning/datasources/prometheus.yml': '''apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true''',
    
        'monitoring/grafana/provisioning/dashboards/dashboard.yml': '''apiVersion: 1
providers:
  - name: 'isp-dashboards'
    orgId: 1
    folder: 'ISP Monitoring'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards''',
      
        'monitoring/alertmanager/alertmanager.yml': '''global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alertas@isp-monitoring.local'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://web:8000/api/alerts/webhook'
        send_resolved: true'''
    }
    
    for file_path, content in configs.items():
        if not Path(file_path).exists():
            with open(file_path, 'w') as f:
                f.write(content)
            print_colored(f"✓ {file_path}")
        else:
            print_colored(f"✓ {file_path} (já existe)")

def build_containers():
    """Construir containers da aplicação"""
    print_header("🔨 CONSTRUINDO CONTAINERS")
    
    try:
        print_colored("Construindo imagens da aplicação...")
        result = subprocess.run([
            'docker-compose', 'build', '--no-cache'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print_colored("✅ Build concluído com sucesso!")
        else:
            print_colored("❌ Erro no build:", Colors.FAIL)
            print_colored(result.stderr, Colors.FAIL)
            return False
            
    except Exception as e:
        print_colored(f"❌ Erro ao construir containers: {e}", Colors.FAIL)
        return False
    
    return True

def start_system():
    """Iniciar o sistema completo"""
    print_header("🚀 INICIANDO SISTEMA")
    
    try:
        # Parar containers existentes
        print_colored("Parando containers existentes...")
        subprocess.run(['docker-compose', 'down'], capture_output=True)
        
        # Iniciar em ordem específica
        print_colored("Iniciando serviços de infraestrutura...")
        result = subprocess.run([
            'docker-compose', 'up', '-d', 'db', 'redis'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print_colored("❌ Erro ao iniciar infraestrutura:", Colors.FAIL)
            print_colored(result.stderr, Colors.FAIL)
            return False
        
        print_colored("Aguardando infraestrutura ficar pronta...")
        time.sleep(15)
        
        # Executar migrações
        print_colored("Executando migrações do banco...")
        migrate_result = subprocess.run([
            'docker-compose', 'exec', '-T', 'db', 'psql',
            '-U', 'postgres', '-d', 'postgres', '-c', 'SELECT 1;'
        ], capture_output=True)
        
        if migrate_result.returncode == 0:
            subprocess.run([
                'docker-compose', 'run', '--rm', 'web',
                'python', 'manage.py', 'migrate'
            ], capture_output=True)
            print_colored("✓ Migrações executadas")
        
        # Iniciar aplicação principal
        print_colored("Iniciando aplicação principal...")
        result = subprocess.run([
            'docker-compose', 'up', '-d', 'web', 'rq_worker', 'scheduler'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print_colored("❌ Erro ao iniciar aplicação:", Colors.FAIL)
            print_colored(result.stderr, Colors.FAIL)
            return False
        
        print_colored("Aguardando aplicação ficar pronta...")
        time.sleep(20)
        
        # Iniciar monitoramento
        print_colored("Iniciando sistema de monitoramento...")
        result = subprocess.run([
            'docker-compose', 'up', '-d'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print_colored("❌ Erro ao iniciar monitoramento:", Colors.FAIL)
            print_colored(result.stderr, Colors.FAIL)
            return False
        
        print_colored("✅ Sistema iniciado com sucesso!")
        return True
        
    except Exception as e:
        print_colored(f"❌ Erro ao iniciar sistema: {e}", Colors.FAIL)
        return False

def wait_for_services():
    """Aguardar serviços ficarem prontos"""
    print_header("⏳ AGUARDANDO SERVIÇOS")
    
    services = {
        'Django App': 'http://localhost:8000/api/health/',
        'Prometheus': 'http://localhost:9090/-/healthy',
        'Grafana': 'http://localhost:3000/api/health'
    }
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        all_ready = True
        attempt += 1
        
        print_colored(f"\nTentativa {attempt}/{max_attempts}")
        
        for service, url in services.items():
            try:
                import requests
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print_colored(f"✓ {service}: Pronto")
                else:
                    print_colored(f"⏳ {service}: Aguardando... (Status: {response.status_code})")
                    all_ready = False
            except:
                print_colored(f"⏳ {service}: Aguardando...")
                all_ready = False
        
        if all_ready:
            print_colored("\n✅ Todos os serviços estão prontos!", Colors.GREEN)
            return True
        
        time.sleep(10)
    
    print_colored("\n⚠️  Alguns serviços podem ainda estar inicializando", Colors.WARNING)
    return False

def create_superuser():
    """Criar superusuário Django se não existir"""
    print_header("👤 CONFIGURANDO USUÁRIO ADMIN")
    
    try:
        result = subprocess.run([
            'docker-compose', 'exec', '-T', 'web',
            'python', 'manage.py', 'shell', '-c',
            "from django.contrib.auth.models import User; "
            "User.objects.filter(username='admin').exists() or "
            "User.objects.create_superuser('admin', 'admin@localhost', 'admin123')"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print_colored("✓ Usuário admin configurado (admin/admin123)")
        else:
            print_colored("⚠️  Erro ao criar usuário admin", Colors.WARNING)
            
    except Exception as e:
        print_colored(f"⚠️  Erro ao configurar usuário: {e}", Colors.WARNING)

def show_status():
    """Mostrar status dos serviços"""
    print_header("📊 STATUS DOS SERVIÇOS")
    
    try:
        result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True)
        print(result.stdout)
    except:
        print_colored("Erro ao obter status dos serviços", Colors.FAIL)

def print_access_info():
    """Imprimir informações de acesso"""
    print_header("🌐 INFORMAÇÕES DE ACESSO")
    
    info = f"""
{Colors.CYAN}📱 APLICAÇÃO PRINCIPAL{Colors.ENDC}
• Django Admin:       http://localhost:8000/admin/
• API:               http://localhost:8000/api/
• Health Check:      http://localhost:8000/api/health/

{Colors.CYAN}📊 MONITORAMENTO{Colors.ENDC}
• Grafana:           http://localhost:3000/
  └─ Login:          admin / admin123
• Prometheus:        http://localhost:9090/
• Alertmanager:      http://localhost:9093/

{Colors.CYAN}📋 MÉTRICAS E LOGS{Colors.ENDC}
• Métricas:          http://localhost:8000/api/metrics/
• Status Alertas:    http://localhost:8000/api/alerts/status/
• Logs da App:       ./logs/
• Logs Docker:       docker-compose logs -f

{Colors.CYAN}🔧 COMANDOS ÚTEIS{Colors.ENDC}
• Ver logs:          python start_system.py logs
• Parar sistema:     python start_system.py stop
• Reiniciar:         python start_system.py restart
• Status:            python start_system.py status
"""
    print(info)

def main():
    """Função principal"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'stop':
            print_header("🛑 PARANDO SISTEMA")
            subprocess.run(['docker-compose', 'down'])
            print_colored("✅ Sistema parado")
            return
            
        elif command == 'restart':
            print_header("🔄 REINICIANDO SISTEMA")
            subprocess.run(['docker-compose', 'down'])
            time.sleep(5)
            start_system()
            wait_for_services()
            print_access_info()
            return
            
        elif command == 'status':
            show_status()
            return
            
        elif command == 'logs':
            subprocess.run(['docker-compose', 'logs', '-f'])
            return
            
        elif command == 'build':
            build_containers()
            return
    
    # Inicialização completa
    print_colored(f"""
{Colors.BOLD}{Colors.BLUE}
╔══════════════════════════════════════════════════════════════╗
║                    SISTEMA ISP - INICIALIZAÇÃO               ║
║              Aplicação Principal + Monitoramento             ║
╚══════════════════════════════════════════════════════════════╝
{Colors.ENDC}""")
    
    # Verificar pré-requisitos
    if not check_requirements():
        sys.exit(1)
    
    # Preparar ambiente
    create_directories()
    check_env_file()
    setup_monitoring_configs()
    
    # Construir e iniciar
    if not build_containers():
        sys.exit(1)
    
    if not start_system():
        sys.exit(1)
    
    # Configurar usuário admin
    create_superuser()
    
    # Aguardar serviços
    wait_for_services()
    
    # Mostrar informações
    show_status()
    print_access_info()
    
    print_colored(f"\n{Colors.BOLD}{Colors.GREEN}🎉 SISTEMA INICIADO COM SUCESSO!{Colors.ENDC}")
    print_colored(f"Use 'python start_system.py stop' para parar o sistema")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n⏹️  Inicialização interrompida pelo usuário", Colors.WARNING)
        sys.exit(1)
    except Exception as e:
        print_colored(f"\n❌ Erro inesperado: {e}", Colors.FAIL)
        sys.exit(1)