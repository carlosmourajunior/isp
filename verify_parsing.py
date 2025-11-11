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
    print("🔍 Verificando alarmes major após nova coleta...")
    
    # Contar total de alarmes major
    major_alarms = OltAlarm.objects.filter(severity='major').count()
    print(f"📊 Total de alarmes major no banco: {major_alarms}")
    
    # Verificar os últimos alarmes major coletados
    print("\n🔍 Verificando os últimos 10 alarmes major:")
    latest_major = OltAlarm.objects.filter(severity='major').order_by('-collected_at')[:10]
    
    correctly_parsed = 0
    incorrectly_parsed = 0
    
    for alarm in latest_major:
        entity_ok = alarm.entity and alarm.entity.startswith('[')
        if entity_ok:
            correctly_parsed += 1
            status = "✅"
        else:
            incorrectly_parsed += 1
            status = "❌"
            
        print(f"  {status} ID: {alarm.id}")
        print(f"     Entity: '{alarm.entity}'")
        print(f"     Desc: {alarm.description[:80]}...")
        print(f"     Collected: {alarm.collected_at}")
        print()
    
    print(f"📈 Resumo da análise:")
    print(f"  ✅ Corretamente parseados: {correctly_parsed}")
    print(f"  ❌ Incorretamente parseados: {incorrectly_parsed}")
    
    if incorrectly_parsed == 0:
        print("🎉 Todos os alarmes major estão sendo parseados corretamente!")
    else:
        print(f"⚠️  {incorrectly_parsed} alarmes ainda têm problemas de parsing.")