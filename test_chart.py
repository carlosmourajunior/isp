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

def test_chart_endpoint():
    client = Client()
    
    print("=== Testando endpoint /api/olt/chart-data/ ===")
    response = client.get('/api/olt/chart-data/')
    print(f"Status: {response.status_code}")
    
    if response.status_code == 401:
        print("⚠️ Endpoint protegido por autenticação (correto)")
        print("Resposta:", response.json())
    elif response.status_code == 200:
        data = response.json()
        print(f"✅ Sucesso! Dados retornados:")
        print(f"  Labels: {len(data.get('labels', []))} pontos")
        print(f"  Datasets: {len(data.get('datasets', []))} séries")
        if 'summary' in data:
            summary = data['summary']
            print(f"  CPU atual: {summary.get('current_cpu')}%")
            print(f"  Memória atual: {summary.get('current_memory')}%")
            print(f"  Amostras: {summary.get('total_samples')}")
    else:
        print(f"❌ Erro: {response.status_code}")
        print(response.content.decode())

if __name__ == '__main__':
    test_chart_endpoint()