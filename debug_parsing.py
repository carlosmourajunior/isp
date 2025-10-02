#!/usr/bin/env python
"""
Script para debugar parsing de slots e temperaturas
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.utils import OltSystemCollector

def debug_parsing():
    """Debug do parsing de dados"""
    try:
        collector = OltSystemCollector()
        net_connect = collector.connect()
        
        print("=== TESTANDO SLOTS ===")
        slots_output = net_connect.send_command("show equipment slot")
        print("Raw output:")
        print(slots_output)
        print("\nParsed data:")
        slots_data = collector._parse_slots(slots_output)
        print(slots_data)
        
        print("\n=== TESTANDO TEMPERATURAS ===")
        temp_output = net_connect.send_command("show equipment temperature")
        print("Raw output:")
        print(temp_output[:500] + "..." if len(temp_output) > 500 else temp_output)
        print("\nParsed data:")
        temp_data = collector._parse_temperature(temp_output)
        print(temp_data)
        
        collector.disconnect(net_connect)
        
    except Exception as e:
        print(f"Erro: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_parsing()