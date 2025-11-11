#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.models import OltAlarm
from olt.utils import olt_connector

# Limpar alarmes antigos para testar com dados frescos
print('Removendo alarmes antigos...')
OltAlarm.objects.all().delete()

print('Coletando novos alarmes...')
connector = olt_connector()
collected_count = connector.collect_all_alarms()

print(f'Alarmes coletados: {collected_count}')

# Verificar alguns dos alarmes com o novo parsing
print()
print('=== VERIFICANDO ALARMES COM NOVO PARSING ===')

# Buscar alarmes que podem ter o novo formato
parsed_alarms = OltAlarm.objects.filter(entity__contains='[').order_by('-collected_at')[:5]
print(f'Alarmes com parsing específico encontrados: {parsed_alarms.count()}')

for alarm in parsed_alarms:
    print(f'Entidade: {alarm.entity}')
    print(f'Descrição: {alarm.description}')
    print(f'Severidade: {alarm.severity} | Ativo: {alarm.is_active}')
    if alarm.alarm_time:
        print(f'Timestamp: {alarm.alarm_time}')
    print('---')

# Verificar fallbacks também
fallback_alarms = OltAlarm.objects.exclude(entity__contains='[').order_by('-collected_at')[:3]
print(f'\nAlarmes com parsing genérico: {fallback_alarms.count()}')
for alarm in fallback_alarms:
    entity_str = alarm.entity or "N/A"
    desc_str = alarm.description[:50] + "..." if len(alarm.description) > 50 else alarm.description
    print(f'Entidade: {entity_str} | Descrição: {desc_str}')