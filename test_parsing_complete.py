#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.utils import olt_connector

# Testar o novo parsing com múltiplos exemplos
connector = olt_connector()

test_cases = [
    '[72/09/26 17:08:14] major alarm cleared for ONU RCMG:19896C04 (goretegomes) - PON 1/1/2/8/61 signal lost',
    '[72/09/26 16:55:30] critical alarm raised for ONU RCMG:12345678 (cliente_teste) - Line fault detected',
    '[72/09/26 15:30:45] minor alarm cleared for ONU RCMG:87654321 (outro_cliente) - Power levels abnormal',
    'ont 1/1/2/8/104 configuration changed',  # Formato antigo para testar fallback
]

print('=== TESTE COMPLETO DO PARSING DE ALARMES ===')
for i, test_line in enumerate(test_cases, 1):
    print(f'\n--- TESTE {i} ---')
    print(f'Linha original: {test_line}')
    
    # Testar o parsing específico
    result = connector._parse_specific_alarm_format(test_line, 'major')
    
    if result and 'entity' in result and '[' in result['entity']:
        print('✅ Parsing específico bem-sucedido!')
        print(f'  Severidade: {result["severity"]}')
        print(f'  Entidade: {result["entity"]}')
        print(f'  Descrição: {result["description"]}')
        print(f'  Ativo: {result["is_active"]}')
        print(f'  Timestamp: {result.get("alarm_time")}')
    else:
        print('➡️ Usando parsing genérico (fallback)')
        result = connector._parse_generic_alarm_format(test_line, 'major')
        if result:
            print(f'  Severidade: {result.get("severity", "N/A")}')
            print(f'  Entidade: {result.get("entity", "N/A")}')
            print(f'  Descrição: {result.get("description", "N/A")[:100]}...')
            print(f'  Ativo: {result.get("is_active", "N/A")}')
            print(f'  Timestamp: {result.get("alarm_time", "N/A")}')
        else:
            print('❌ Nenhum parsing funcionou')