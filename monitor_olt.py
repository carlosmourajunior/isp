#!/usr/bin/env python3
"""
Script de monitoramento das coletas automáticas da OLT
Mostra dados em tempo real e estatísticas
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def monitor_collections():
    from olt.models import OltSystemStats
    from django.utils import timezone
    from datetime import timedelta
    import time
    
    print("📊 === MONITOR DE COLETA AUTOMÁTICA OLT ===")
    print("🔄 Atualizando a cada 30 segundos... (Ctrl+C para sair)")
    print()
    
    try:
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            
            print("📊 === MONITOR DE COLETA AUTOMÁTICA OLT ===")
            print(f"🕐 Última atualização: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}")
            print()
            
            # Estatísticas gerais
            total_records = OltSystemStats.objects.count()
            print(f"📈 Total de registros históricos: {total_records}")
            
            # Dados das últimas 24h
            last_24h = timezone.now() - timedelta(hours=24)
            recent_count = OltSystemStats.objects.filter(measured_at__gte=last_24h).count()
            print(f"⏰ Registros das últimas 24h: {recent_count}")
            
            # Última medição
            latest = OltSystemStats.get_latest()
            if latest:
                print()
                print("📊 === ÚLTIMA MEDIÇÃO ===")
                print(f"🖥️  CPU: {latest.cpu_percent}%")
                print(f"💾 Memória: {latest.mem_percent}%") 
                print(f"📡 Modelo: {latest.model}")
                print(f"⏱️  Uptime: {latest.uptime_days} dias")
                print(f"🔧 Slots: {latest.operational_slots}/{latest.total_slots}")
                if latest.avg_temperature:
                    print(f"🌡️  Temperatura: {latest.avg_temperature:.1f}°C")
                print(f"📅 Coletado em: {latest.measured_at.strftime('%d/%m/%Y %H:%M:%S')}")
                
                # Próxima coleta (estimativa)
                next_collection = latest.measured_at + timedelta(hours=1)
                time_until_next = next_collection - timezone.now()
                if time_until_next.total_seconds() > 0:
                    minutes_left = int(time_until_next.total_seconds() / 60)
                    print(f"⏳ Próxima coleta em: ~{minutes_left} minutos")
                else:
                    print("⏰ Coleta em atraso ou em andamento...")
            else:
                print("❌ Nenhum dado encontrado")
            
            # Histórico recente (últimos 5)
            print()
            print("📈 === HISTÓRICO RECENTE ===")
            recent_stats = OltSystemStats.objects.order_by('-measured_at')[:5]
            
            for i, stat in enumerate(recent_stats):
                status = "🟢" if i == 0 else "📊"
                print(f"{status} {stat.measured_at.strftime('%H:%M')} - "
                      f"CPU: {stat.cpu_percent}%, "
                      f"Mem: {stat.mem_percent}%, "
                      f"Temp: {stat.avg_temperature:.1f}°C" if stat.avg_temperature else "Temp: --°C")
            
            # Estatísticas das últimas 24h
            if recent_count > 1:
                recent_stats_list = list(OltSystemStats.objects.filter(
                    measured_at__gte=last_24h
                ).order_by('-measured_at'))
                
                cpu_values = [s.cpu_percent for s in recent_stats_list if s.cpu_percent is not None]
                mem_values = [s.mem_percent for s in recent_stats_list if s.mem_percent is not None]
                
                if cpu_values and mem_values:
                    print()
                    print("📊 === ESTATÍSTICAS 24H ===")
                    print(f"🖥️  CPU - Média: {sum(cpu_values)/len(cpu_values):.1f}%, "
                          f"Min: {min(cpu_values)}%, Max: {max(cpu_values)}%")
                    print(f"💾 Memória - Média: {sum(mem_values)/len(mem_values):.1f}%, "
                          f"Min: {min(mem_values)}%, Max: {max(mem_values)}%")
            
            print()
            print("🛠  Comandos úteis:")
            print("   Ver logs: docker compose -f docker-compose.scheduler.yml logs -f")
            print("   Coleta manual: docker compose exec web python manage.py collect_olt_periodic --once")
            
            # Aguardar 30 segundos
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n👋 Monitor finalizado pelo usuário")

if __name__ == '__main__':
    monitor_collections()