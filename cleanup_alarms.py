#!/usr/bin/env python
import os
import sys
import django

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.models import OltAlarm

def cleanup_malformed_alarms():
    # Buscar alarmes major
    major_alarms = OltAlarm.objects.filter(severity='major')
    
    print(f"Total de alarmes major: {major_alarms.count()}")
    print("\nAlarmes major existentes:")
    
    for alarm in major_alarms:
        entity_preview = repr(alarm.entity) if alarm.entity else 'NULL'
        desc_preview = alarm.description[:50] + '...' if alarm.description else 'NULL'
        print(f"ID: {alarm.id}, Entity: {entity_preview}, Desc: {desc_preview}")
    
    print("\n" + "="*50)
    
    # Identificar alarmes malformados (entidade não começa com [ ou é nula)
    bad_alarms = []
    for alarm in major_alarms:
        if not alarm.entity or not alarm.entity.startswith('['):
            bad_alarms.append(alarm)
    
    print(f"Encontrados {len(bad_alarms)} alarmes com entidade malformada:")
    for alarm in bad_alarms:
        print(f"  ID: {alarm.id}, Entity: {repr(alarm.entity)}")
    
    if bad_alarms:
        print(f"\nRemovendo {len(bad_alarms)} alarmes malformados...")
        for alarm in bad_alarms:
            alarm.delete()
        print("Remoção concluída!")
    else:
        print("\nNenhum alarme malformado encontrado.")
    
    # Verificar resultado final
    remaining_major = OltAlarm.objects.filter(severity='major').count()
    print(f"\nAlarmes major restantes: {remaining_major}")

if __name__ == '__main__':
    cleanup_malformed_alarms()