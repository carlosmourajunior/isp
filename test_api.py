#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

from django.test import Client
import json

def test_api_endpoints():
    client = Client()
    
    # Testar endpoint de sistema
    print("=== Testando endpoint /api/olt/system-stats/ ===")
    response = client.get('/api/olt/system-stats/')
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"CPU: {data.get('cpu_percent', 'N/A')}%")
        print(f"Memoria: {data.get('mem_percent', 'N/A')}%")
        print(f"Modelo: {data.get('model', 'N/A')}")
        print(f"Uptime: {data.get('uptime_days', 'N/A')} dias")
    else:
        print(f"Erro: {response.content.decode()}")
    
    print("\n=== Testando endpoint /api/olt/system-history/ ===")
    response = client.get('/api/olt/system-history/')
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Registros retornados: {len(data)}")
        if data:
            latest = data[0]
            print(f"Ultimo registro:")
            print(f"  CPU: {latest.get('cpu_percent')}%")
            print(f"  Memoria: {latest.get('mem_percent')}%")
            print(f"  Modelo: {latest.get('model')}")
            print(f"  Data: {latest.get('measured_at')}")
    else:
        print(f"Erro: {response.content.decode()}")

if __name__ == '__main__':
    test_api_endpoints()