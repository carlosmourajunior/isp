#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.utils import olt_connector

# Testar o novo parsing com o exemplo fornecido
connector = olt_connector()

# Simular a linha de exemplo
test_line = '[72/09/26 17:08:14] major alarm cleared for ONU RCMG:19896C04 (goretegomes) - PON 1/1/2/8/61 signal lost'

print('=== TESTE DO NOVO PARSING ===')
print(f'Linha original: {test_line}')
print()

# Testar o parsing específico
result = connector._parse_specific_alarm_format(test_line, 'major')

if result:
    print('✅ Parsing bem-sucedido!')
    print(f'Severidade: {result["severity"]}')
    print(f'Entidade: {result["entity"]}')
    print(f'Descrição: {result["description"]}')
    print(f'Ativo: {result["is_active"]}')
    print(f'Timestamp: {result.get("alarm_time")}')
else:
    print('❌ Parsing não funcionou, testando fallback...')
    result = connector._parse_generic_alarm_format(test_line, 'major')
    if result:
        print(f'Fallback funcionou: {result}')
    else:
        print('Nenhum parsing funcionou')