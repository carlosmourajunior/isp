#!/usr/bin/env python
import os
import sys
import django

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.utils import olt_connector
from olt.models import OltAlarm

def test_parsing_and_saving():
    # Simular linha de alarme major
    test_line = "[72/09/26 17:26:56] major alarm cleared for ONU RCMG:19896C04 (goretegomes) - PON 1/1/2/7/8 (service affecting) : Received optical signal too low"
    
    # Criar instância do connector
    connector = olt_connector()
    
    # Testar o parsing específico
    print("=== TESTANDO PARSING ESPECÍFICO ===")
    alarm_data = connector._parse_specific_alarm_format(test_line, 'major')
    
    if alarm_data:
        print("PARSING ESPECÍFICO FUNCIONOU!")
        print("Dados extraídos:")
        for key, value in alarm_data.items():
            print(f"  {key}: {repr(value)}")
        
        # Testar salvamento
        print("\n=== TESTANDO SALVAMENTO ===")
        try:
            # Verificar se já existe um alarme similar (evitar duplicatas)
            existing = OltAlarm.objects.filter(
                entity=alarm_data['entity'],
                description=alarm_data['description']
            ).first()
            
            if existing:
                print(f"Alarme similar já existe: ID {existing.id}")
                print(f"  Entity: {repr(existing.entity)}")
                print(f"  Description: {repr(existing.description)}")
            else:
                # Criar novo alarme
                new_alarm = OltAlarm.objects.create(**alarm_data)
                print(f"Novo alarme criado: ID {new_alarm.id}")
                print(f"  Entity: {repr(new_alarm.entity)}")
                print(f"  Description: {repr(new_alarm.description)}")
                
                # Remover o alarme de teste
                new_alarm.delete()
                print("Alarme de teste removido.")
                
        except Exception as e:
            print(f"ERRO ao salvar: {str(e)}")
    else:
        print("PARSING ESPECÍFICO FALHOU!")
        
        # Testar parsing genérico como fallback
        print("\n=== TESTANDO PARSING GENÉRICO ===")
        generic_data = connector._parse_generic_alarm_format(test_line, 'major')
        
        if generic_data:
            print("PARSING GENÉRICO FUNCIONOU!")
            print("Dados extraídos:")
            for key, value in generic_data.items():
                print(f"  {key}: {repr(value)}")
        else:
            print("PARSING GENÉRICO TAMBÉM FALHOU!")

if __name__ == '__main__':
    test_parsing_and_saving()