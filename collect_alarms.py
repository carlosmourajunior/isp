#!/usr/bin/env python3
import os
import sys
import django
from django.conf import settings

# Configurar Django
sys.path.append('/code')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.utils import olt_connector

if __name__ == "__main__":
    print("🔍 Coletando alarmes da OLT...")
    
    try:
        # Conectar diretamente à OLT e coletar alarmes
        connector = olt_connector()
        collected_count = connector.collect_all_alarms()
        
        print(f"✅ Coleta concluída: {collected_count} alarmes coletados")
        
        # Verificar quantos alarmes major foram coletados
        from olt.models import OltAlarm
        major_alarms = OltAlarm.objects.filter(severity='major').count()
        print(f"📊 Total de alarmes major no banco: {major_alarms}")
        
        # Mostrar os últimos 5 alarmes major
        if major_alarms > 0:
            print("\n🔍 Últimos 5 alarmes major:")
            latest_major = OltAlarm.objects.filter(severity='major').order_by('-collected_at')[:5]
            for alarm in latest_major:
                print(f"  ID: {alarm.id}, Entity: '{alarm.entity}', Desc: {alarm.description[:50]}...")
                
    except Exception as e:
        print(f"❌ Erro na coleta: {e}")
        import traceback
        traceback.print_exc()