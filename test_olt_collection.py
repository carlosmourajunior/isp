#!/usr/bin/env python
"""
Script para testar a coleta de dados da OLT
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.utils import OltSystemCollector

def test_olt_collection():
    """Testa a coleta de dados da OLT"""
    try:
        print("Iniciando coleta de dados da OLT...")
        collector = OltSystemCollector()
        result = collector.collect_all_system_data()
        
        if result:
            print("✅ Coleta realizada com sucesso!")
            print(f"Sistema: {result['system_info']}")
            print(f"Slots: {result['slots'].count() if result['slots'] else 0}")
            print(f"Temperaturas: {result['temperatures'].count() if result['temperatures'] else 0}")
        else:
            print("❌ Falha na coleta de dados")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")

if __name__ == "__main__":
    test_olt_collection()