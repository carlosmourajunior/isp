#!/usr/bin/env python3
"""
Script para configurar e inicializar o sistema de monitoramento
"""

import os
import sys
import subprocess
import time

def create_directories():
    """Criar diretórios necessários para logs e dados"""
    directories = [
        'logs',
        'data/logs',
        'data/grafana',
        'data/prometheus',
        'data/alertmanager'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Diretório criado: {directory}")

def check_docker():
    """Verificar se Docker está instalado e rodando"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Docker encontrado:", result.stdout.strip())
        else:
            print("❌ Docker não encontrado")
            return False
            
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Docker Compose encontrado:", result.stdout.strip())
        else:
            print("❌ Docker Compose não encontrado")
            return False
            
        return True
    except FileNotFoundError:
        print("❌ Docker não está instalado")
        return False

def setup_monitoring():
    """Configurar e iniciar o monitoramento"""
    print("🚀 Iniciando setup do monitoramento...")
    
    # Verificar dependências
    if not check_docker():
        print("❌ Por favor, instale o Docker e Docker Compose primeiro")
        return False
    
    # Criar diretórios
    create_directories()
    
    print("\n📦 Construindo e iniciando containers...")
    
    try:
        # Parar containers existentes
        subprocess.run(['docker-compose', '-f', 'docker-compose.monitoring.yml', 'down'], 
                      capture_output=True)
        
        # Construir e iniciar containers
        result = subprocess.run([
            'docker-compose', '-f', 'docker-compose.monitoring.yml', 
            'up', '-d', '--build'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Containers iniciados com sucesso")
        else:
            print("❌ Erro ao iniciar containers:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Erro ao executar docker-compose: {e}")
        return False
    
    # Aguardar serviços ficarem prontos
    print("\n⏳ Aguardando serviços ficarem prontos...")
    time.sleep(30)
    
    # Verificar status dos serviços
    check_services()
    
    print_access_urls()
    
    return True

def check_services():
    """Verificar status dos serviços"""
    services = {
        'Django App': 'http://localhost:8000/api/health/',
        'Prometheus': 'http://localhost:9090/-/healthy',
        'Grafana': 'http://localhost:3000/api/health',
        'Alertmanager': 'http://localhost:9093/-/healthy'
    }
    
    print("\n🔍 Verificando status dos serviços...")
    
    import requests
    
    for service, url in services.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✓ {service}: OK")
            else:
                print(f"⚠️  {service}: Status {response.status_code}")
        except requests.exceptions.RequestException:
            print(f"❌ {service}: Não disponível")

def print_access_urls():
    """Imprimir URLs de acesso"""
    print("\n🌐 URLs de Acesso:")
    print("=" * 50)
    print("📊 Django App:        http://localhost:8000")
    print("📈 Prometheus:        http://localhost:9090")
    print("📊 Grafana:           http://localhost:3000")
    print("   └─ Login:          admin / admin123")
    print("🚨 Alertmanager:      http://localhost:9093")
    print("📋 Health Check:      http://localhost:8000/api/health/")
    print("📊 Métricas:          http://localhost:8000/api/metrics/")
    print("🔍 Logs da App:       ./logs/")
    print("=" * 50)

def stop_monitoring():
    """Parar o monitoramento"""
    print("🛑 Parando sistema de monitoramento...")
    
    try:
        result = subprocess.run([
            'docker-compose', '-f', 'docker-compose.monitoring.yml', 'down'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Monitoramento parado com sucesso")
        else:
            print("❌ Erro ao parar monitoramento:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Erro ao parar monitoramento: {e}")

def restart_monitoring():
    """Reiniciar o monitoramento"""
    print("🔄 Reiniciando sistema de monitoramento...")
    stop_monitoring()
    time.sleep(5)
    setup_monitoring()

def show_logs():
    """Mostrar logs dos containers"""
    print("📋 Logs dos containers de monitoramento:")
    
    try:
        subprocess.run([
            'docker-compose', '-f', 'docker-compose.monitoring.yml', 'logs', '-f'
        ])
    except KeyboardInterrupt:
        print("\n📋 Logs interrompidos")

def main():
    """Função principal"""
    if len(sys.argv) < 2:
        print("📊 Sistema de Monitoramento ISP")
        print("=" * 40)
        print("Uso: python setup_monitoring.py [comando]")
        print()
        print("Comandos disponíveis:")
        print("  start    - Iniciar monitoramento")
        print("  stop     - Parar monitoramento")
        print("  restart  - Reiniciar monitoramento")
        print("  status   - Verificar status")
        print("  logs     - Mostrar logs")
        print("  urls     - Mostrar URLs de acesso")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        setup_monitoring()
    elif command == 'stop':
        stop_monitoring()
    elif command == 'restart':
        restart_monitoring()
    elif command == 'status':
        check_services()
    elif command == 'logs':
        show_logs()
    elif command == 'urls':
        print_access_urls()
    else:
        print(f"❌ Comando desconhecido: {command}")

if __name__ == "__main__":
    main()