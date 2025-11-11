#!/usr/bin/env python3
import os
import sys
import django
from django.conf import settings

# Configurar Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.models import OltAlarm

if __name__ == "__main__":
    print("🔍 Debugando processo de parsing dos alarmes...")
    
    # Pegar um alarme da base que deveria estar mal parseado
    recent_alarms = OltAlarm.objects.filter(severity='major').order_by('-collected_at')[:3]
    
    print("\n📋 Alarmes recentes coletados:")
    for alarm in recent_alarms:
        print(f"\nID: {alarm.id}")
        print(f"Severity: {alarm.severity}")
        print(f"Entity: '{alarm.entity}'")  
        print(f"Description: '{alarm.description}'")
        print(f"Alarm Time: {alarm.alarm_time}")
        print(f"Collected At: {alarm.collected_at}")
        print(f"Is Active: {alarm.is_active}")
        print("-" * 50)
        
        # Testar o parsing manualmente
        print("🧪 Testando re-parsing manual da descrição:")
        
        # Simular linha original que geraria estes dados
        if alarm.description and '[72/' in alarm.description:
            # Se a descrição contém timestamp, o problema pode ser que a entity está sendo sobrescrita
            print(f"🔍 Descrição contém timestamp: {alarm.description[:100]}...")
            
            # Vamos verificar se o entity deveria ser o timestamp + info
            if alarm.description.startswith('[72/'):
                # A descrição inteira deveria ser dividida
                parts = alarm.description.split(' - ', 1)
                if len(parts) == 2:
                    expected_entity = parts[0]
                    expected_desc = parts[1]
                    print(f"✨ Entity esperada: '{expected_entity}'")
                    print(f"✨ Descrição esperada: '{expected_desc}'")
                    print(f"❌ Entity atual: '{alarm.entity}'")
                    print(f"❌ Descrição atual: '{alarm.description}'")
                    
    print("\n🔎 Vou simular o parsing de uma linha de exemplo...")
    
    # Simular uma linha de alarme major típica
    test_line = "[72/09/26 17:26:56] major alarm cleared for ONU RCMG:19896C04 (goretegomes) - PON 1/1/2/7/8 (service affecting) : Received optical signal too low"
    
    print(f"📝 Linha de teste: {test_line}")
    
    # Testar o regex manualmente
    import re
    major_alarm_pattern = r'(\[[\d/\s:]+\])\s*(major|critical|minor|warning)\s*alarm\s*(cleared|raised)?\s*for\s*(?:ONU\s+)?([A-Z0-9:]+)\s*\(([^)]+)\)\s*-\s*(.*)'
    
    match = re.match(major_alarm_pattern, test_line, re.IGNORECASE)
    if match:
        timestamp_str = match.group(1)
        severity = match.group(2).lower()
        action = match.group(3) or 'active'
        onu_serial = match.group(4)
        client_name = match.group(5)
        remaining_content = match.group(6)
        
        entity = f"{timestamp_str} {severity} alarm {action} for {onu_serial} ({client_name})"
        description = remaining_content.strip()
        
        print(f"✅ Regex match encontrado!")
        print(f"  📅 Timestamp: '{timestamp_str}'")
        print(f"  🚨 Severity: '{severity}'")
        print(f"  🔄 Action: '{action}'")
        print(f"  📡 ONU Serial: '{onu_serial}'")
        print(f"  👤 Cliente: '{client_name}'")
        print(f"  📄 Remaining: '{remaining_content}'")
        print(f"  🏷️ Entity final: '{entity}'")
        print(f"  📝 Description final: '{description}'")
    else:
        print("❌ Regex não fez match!")