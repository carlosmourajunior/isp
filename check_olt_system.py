#!/usr/bin/env python3
"""
Script de verificação do sistema de coleta automática
Verifica se todos os componentes estão funcionando
"""

import os
import sys
import django
import subprocess

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def check_docker_service(service_name, compose_file="docker-compose.yml"):
    """Verifica se um serviço Docker está rodando"""
    try:
        if compose_file == "docker-compose.yml":
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"], 
                capture_output=True, text=True, cwd="/code"
            )
        else:
            result = subprocess.run(
                ["docker", "compose", "-f", compose_file, "ps", "--format", "json"], 
                capture_output=True, text=True, cwd="/code"
            )
        
        return service_name.lower() in result.stdout.lower() and "running" in result.stdout.lower()
    except:
        return False

def check_system():
    from olt.models import OltSystemStats
    from django.utils import timezone
    from datetime import timedelta
    
    print("🔍 === VERIFICAÇÃO DO SISTEMA DE COLETA AUTOMÁTICA ===")
    print()
    
    # 1. Verificar serviços Docker
    print("🐳 === VERIFICAÇÃO DOS SERVIÇOS DOCKER ===")
    
    services_to_check = [
        ("web", "docker-compose.yml", "Aplicação principal"),
        ("db", "docker-compose.yml", "Banco de dados"),
        ("redis", "docker-compose.yml", "Cache Redis"),
        ("olt-scheduler", "docker-compose.scheduler.yml", "Scheduler OLT")
    ]
    
    all_services_ok = True
    for service, compose_file, description in services_to_check:
        is_running = check_docker_service(service, compose_file)
        status = "✅" if is_running else "❌"
        print(f"{status} {description} ({service})")
        if not is_running:
            all_services_ok = False
    
    print()
    
    # 2. Verificar dados históricos
    print("📊 === VERIFICAÇÃO DOS DADOS HISTÓRICOS ===")
    
    total_records = OltSystemStats.objects.count()
    print(f"📈 Total de registros: {total_records}")
    
    if total_records == 0:
        print("❌ Nenhum dado histórico encontrado")
        print("💡 Solução: Execute 'docker compose exec web python manage.py collect_olt_periodic --once'")
        return False
    
    # 3. Verificar dados recentes
    latest = OltSystemStats.get_latest()
    if latest:
        time_since_last = timezone.now() - latest.measured_at
        hours_since_last = time_since_last.total_seconds() / 3600
        
        print(f"🕐 Última coleta: {latest.measured_at.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"⏱️  Tempo desde última: {hours_since_last:.1f} horas")
        
        if hours_since_last > 2:  # Mais de 2 horas é suspeito
            print("⚠️ Última coleta foi há mais de 2 horas - scheduler pode estar parado")
            all_services_ok = False
        else:
            print("✅ Coleta recente está OK")
            
        print(f"📊 Dados da última coleta:")
        print(f"   CPU: {latest.cpu_percent}%")
        print(f"   Memória: {latest.mem_percent}%")
        print(f"   Modelo: {latest.model}")
    
    print()
    
    # 4. Verificar dados das últimas 24h
    print("📅 === VERIFICAÇÃO DAS ÚLTIMAS 24H ===")
    
    last_24h = timezone.now() - timedelta(hours=24)
    recent_count = OltSystemStats.objects.filter(measured_at__gte=last_24h).count()
    
    print(f"📈 Registros das últimas 24h: {recent_count}")
    
    expected_collections = min(24, total_records)  # Máximo de 24 coletas por dia
    
    if recent_count == 0:
        print("❌ Nenhuma coleta nas últimas 24h")
        all_services_ok = False
    elif recent_count < expected_collections * 0.8:  # Menos de 80% do esperado
        print(f"⚠️ Poucas coletas nas últimas 24h (esperado: ~{expected_collections})")
    else:
        print("✅ Frequência de coletas está adequada")
    
    print()
    
    # 5. Verificar endpoint da API
    print("🌐 === VERIFICAÇÃO DA API ===")
    
    try:
        from django.test import Client
        client = Client()
        
        # Testar endpoint de dados do gráfico
        response = client.get('/api/olt/chart-data/')
        if response.status_code in [200, 401]:  # 401 é esperado (autenticação)
            print("✅ Endpoint /api/olt/chart-data/ está respondendo")
        else:
            print(f"❌ Endpoint com problema (status: {response.status_code})")
            all_services_ok = False
            
        # Testar endpoint de stats
        response = client.get('/api/olt/system-stats/')
        if response.status_code in [200, 401]:  # 401 é esperado (autenticação)
            print("✅ Endpoint /api/olt/system-stats/ está respondendo")
        else:
            print(f"❌ Endpoint com problema (status: {response.status_code})")
            all_services_ok = False
            
    except Exception as e:
        print(f"❌ Erro ao testar API: {str(e)}")
        all_services_ok = False
    
    print()
    
    # 6. Resultado final
    print("🎯 === RESULTADO DA VERIFICAÇÃO ===")
    
    if all_services_ok and total_records > 0:
        print("✅ Sistema funcionando corretamente!")
        print()
        print("📋 Resumo:")
        print(f"   📊 {total_records} registros históricos")
        print(f"   ⏰ {recent_count} coletas nas últimas 24h")
        print("   🔄 Coleta automática a cada 1 hora")
        print("   📈 Gráficos disponíveis no dashboard")
        print()
        print("🔗 Acesso ao dashboard: http://localhost:8000")
    else:
        print("❌ Sistema com problemas detectados!")
        print()
        print("🛠  Ações sugeridas:")
        if not check_docker_service("olt-scheduler", "docker-compose.scheduler.yml"):
            print("   1. Iniciar scheduler: docker compose -f docker-compose.scheduler.yml up -d")
        if total_records == 0:
            print("   2. Coleta inicial: docker compose exec web python manage.py collect_olt_periodic --once")
        print("   3. Verificar logs: docker compose -f docker-compose.scheduler.yml logs -f")
        print("   4. Reiniciar sistema: ./start_clean.sh")

if __name__ == '__main__':
    check_system()