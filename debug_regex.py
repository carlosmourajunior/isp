#!/usr/bin/env python
import os
import sys
import django
import re

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

def test_regex_parsing():
    # Linha de exemplo que não está sendo parseada corretamente
    test_line = "[72/09/26 17:26:56] major alarm cleared for ONU RCMG:19896C04 (goretegomes) - PON 1/1/2/7/8 (service affecting) : Received optical signal too low"
    
    # Regex atual do código
    major_alarm_pattern = r'(\[[\d/\s:]+\])\s*(major|critical|minor|warning)\s*alarm\s*(cleared|raised)?\s*for\s*(?:ONU\s+)?([A-Z0-9:]+)\s*\(([^)]+)\)\s*-\s*(.*)'
    
    print("Linha de teste:")
    print(repr(test_line))
    print()
    
    print("Regex pattern:")
    print(repr(major_alarm_pattern))
    print()
    
    match = re.match(major_alarm_pattern, test_line, re.IGNORECASE)
    if match:
        print("MATCH ENCONTRADO!")
        print("Grupos:")
        for i, group in enumerate(match.groups(), 1):
            print(f"  Grupo {i}: {repr(group)}")
        
        timestamp_str = match.group(1)
        severity = match.group(2).lower()
        action = match.group(3) or 'active'
        onu_serial = match.group(4)
        client_name = match.group(5)
        remaining_content = match.group(6)
        
        print()
        print("Dados extraídos:")
        print(f"  Timestamp: {repr(timestamp_str)}")
        print(f"  Severity: {repr(severity)}")
        print(f"  Action: {repr(action)}")
        print(f"  ONU Serial: {repr(onu_serial)}")
        print(f"  Client Name: {repr(client_name)}")
        print(f"  Remaining Content: {repr(remaining_content)}")
        
        print()
        print("Como seria salvo:")
        entity = f"{timestamp_str} {severity} alarm {action} for {onu_serial} ({client_name})"
        description = remaining_content.strip()
        print(f"  Entity: {repr(entity)}")
        print(f"  Description: {repr(description)}")
        
    else:
        print("NENHUM MATCH ENCONTRADO!")
        print("O regex não está reconhecendo esta linha.")

if __name__ == '__main__':
    test_regex_parsing()