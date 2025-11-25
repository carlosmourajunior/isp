#!/usr/bin/env python
"""
Script para testar filtros de data na API do IXC
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_api_filters():
    """Testa diferentes filtros na API"""
    print("=== TESTE DE FILTROS NA API IXC ===")
    
    try:
        from olt.client_utils import IxcOSClient
        import requests
        import base64
        from datetime import date
        
        client = IxcOSClient()
        
        # 1. Teste sem filtros
        print(f"\n🔍 === TESTE SEM FILTROS ===")
        
        payload_sem_filtro = {
            'qtype': 'su_oss_chamado.id',
            'query': '0',
            'oper': '>',
            'page': '1',
            'rp': '10',
            'sortname': 'su_oss_chamado.id',
            'sortorder': 'desc'
        }
        
        headers = client.headers.copy()
        headers['ixcsoft'] = 'listar'
        
        response = requests.post(client.base_url, data=payload_sem_filtro, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total = int(data.get('total', 0))
            registros = data.get('registros', [])
            
            print(f"✅ Total sem filtros: {total} OS")
            print(f"📋 Primeiras OS:")
            
            for i, os in enumerate(registros[:3], 1):
                id_os = os.get('id')
                protocolo = os.get('protocolo', 'N/A')
                data_abertura = os.get('data_abertura', 'N/A')
                print(f"   {i}. ID {id_os} - {protocolo} - {data_abertura}")
        else:
            print(f"❌ Erro sem filtros: {response.status_code}")
        
        # 2. Teste com filtro de data (método atual)
        print(f"\n🔍 === TESTE COM FILTRO DE DATA (ATUAL) ===")
        
        payload_data_atual = {
            'qtype': 'su_oss_chamado.data_abertura',
            'query': '2025-11-01',
            'query2': '2025-11-24',
            'oper': 'between',
            'page': '1',
            'rp': '10',
            'sortname': 'su_oss_chamado.id',
            'sortorder': 'desc'
        }
        
        response = requests.post(client.base_url, data=payload_data_atual, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total = int(data.get('total', 0))
            registros = data.get('registros', [])
            
            print(f"✅ Total com filtro data (atual): {total} OS")
            print(f"📋 Primeiras OS:")
            
            for i, os in enumerate(registros[:3], 1):
                id_os = os.get('id')
                protocolo = os.get('protocolo', 'N/A')
                data_abertura = os.get('data_abertura', 'N/A')
                print(f"   {i}. ID {id_os} - {protocolo} - {data_abertura}")
        else:
            print(f"❌ Erro com filtro data: {response.status_code}")
        
        # 3. Teste com filtro de data alternativo
        print(f"\n🔍 === TESTE COM FILTRO DE DATA ALTERNATIVO ===")
        
        payload_data_alt = {
            'qtype': 'su_oss_chamado.data_abertura',
            'query': '2025-11-01 00:00:00',
            'query2': '2025-11-24 23:59:59',
            'oper': 'between',
            'page': '1',
            'rp': '10',
            'sortname': 'su_oss_chamado.data_abertura',
            'sortorder': 'desc'
        }
        
        response = requests.post(client.base_url, data=payload_data_alt, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total = int(data.get('total', 0))
            registros = data.get('registros', [])
            
            print(f"✅ Total com filtro data (alt): {total} OS")
            print(f"📋 Primeiras OS:")
            
            for i, os in enumerate(registros[:3], 1):
                id_os = os.get('id')
                protocolo = os.get('protocolo', 'N/A')
                data_abertura = os.get('data_abertura', 'N/A')
                print(f"   {i}. ID {id_os} - {protocolo} - {data_abertura}")
        else:
            print(f"❌ Erro com filtro data alt: {response.status_code}")
        
        # 4. Teste com filtro de data >= (maior que data)
        print(f"\n🔍 === TESTE COM FILTRO >= 01/NOV ===")
        
        payload_data_ge = {
            'qtype': 'su_oss_chamado.data_abertura',
            'query': '2025-11-01',
            'oper': '>=',
            'page': '1',
            'rp': '10',
            'sortname': 'su_oss_chamado.data_abertura',
            'sortorder': 'desc'
        }
        
        response = requests.post(client.base_url, data=payload_data_ge, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total = int(data.get('total', 0))
            registros = data.get('registros', [])
            
            print(f"✅ Total com filtro >= 01/nov: {total} OS")
            print(f"📋 Primeiras OS:")
            
            for i, os in enumerate(registros[:5], 1):
                id_os = os.get('id')
                protocolo = os.get('protocolo', 'N/A')
                data_abertura = os.get('data_abertura', 'N/A')
                print(f"   {i}. ID {id_os} - {protocolo} - {data_abertura}")
                
            # Verificar se as datas estão realmente >= 01/11
            datas_validas = 0
            for os in registros:
                data_str = os.get('data_abertura', '')
                if data_str and '2025-11' in data_str:
                    datas_validas += 1
            
            print(f"📊 OS com data válida (nov/2025): {datas_validas}/{len(registros)}")
            
        else:
            print(f"❌ Erro com filtro >= : {response.status_code}")
        
        # 5. Teste com apenas data de hoje
        print(f"\n🔍 === TESTE COM FILTRO APENAS HOJE ===")
        
        hoje = date.today()
        payload_hoje = {
            'qtype': 'su_oss_chamado.data_abertura',
            'query': hoje.strftime('%Y-%m-%d'),
            'oper': 'like',
            'page': '1',
            'rp': '10',
            'sortname': 'su_oss_chamado.data_abertura',
            'sortorder': 'desc'
        }
        
        response = requests.post(client.base_url, data=payload_hoje, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total = int(data.get('total', 0))
            registros = data.get('registros', [])
            
            print(f"✅ Total apenas hoje ({hoje}): {total} OS")
            print(f"📋 OS de hoje:")
            
            for i, os in enumerate(registros, 1):
                id_os = os.get('id')
                protocolo = os.get('protocolo', 'N/A')
                data_abertura = os.get('data_abertura', 'N/A')
                print(f"   {i}. ID {id_os} - {protocolo} - {data_abertura}")
        else:
            print(f"❌ Erro com filtro hoje: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 TESTE DE FILTROS API IXC")
    
    sucesso = test_api_filters()
    
    if sucesso:
        print("\n🎉 TESTE CONCLUÍDO!")
    else:
        print("\n❌ TESTE FALHOU")
        sys.exit(1)