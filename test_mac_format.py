#!/usr/bin/env python
import os
import sys
import django

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.utils import olt_connector

# Testar a função create_dict_from_result com dados de exemplo
conn = olt_connector()

# Simular dados da OLT (formato real da saída)
test_data = '''1/1/2/6    1/1/2/6/1     OPTI:35029212 up       up       -22.5       0.8           cliente1                                          cliente1                                          undefined
1/1/2/6    1/1/2/6/2     RCMG:3A88390E up       up       -23.0       0.5           cliente2                                          cliente2                                          undefined
1/1/2/6    1/1/2/6/3     ALCL:B3FD7281 up       up       -23.4       0.6           cliente3                                          cliente3                                          undefined'''

print("=== TESTE DE FORMATAÇÃO DO MAC ===")
result = conn.create_dict_from_result(test_data)

print(f"Dados processados: {len(result)} ONUs")
print()

for i, item in enumerate(result, 1):
    print(f"ONU {i}:")
    print(f"  Serial completo: {item['sernum']}")
    print(f"  MAC formatado:   {item['mac']}")
    print(f"  PON:             {item['pon']}")
    print(f"  Posição:         {item['position']}")
    print()