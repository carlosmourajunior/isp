#!/usr/bin/env python
"""
Teste direto usando exatamente o mesmo formato do exemplo fornecido
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_exact_format():
    """Testa usando exatamente o formato do exemplo fornecido"""
    print("=== TESTE FORMATO EXATO DO EXEMPLO IXC ===")
    
    try:
        import requests
        import base64
        from olt.client_utils import IxcOSClient
        
        # Configurar cliente
        client = IxcOSClient()
        
        # 1. TESTE COM FORMATO ORIGINAL (sem alterações)
        print(f"\n🔍 === FORMATO ORIGINAL ===")
        
        payload_original = {
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
        
        response = requests.post(client.base_url, data=payload_original, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total_original = int(data.get('total', 0))
            print(f"✅ Total original: {total_original} OS")
        else:
            print(f"❌ Erro: {response.status_code}")
            return False
        
        # 2. TESTE EXATO BASEADO NO EXEMPLO (ID específico)
        print(f"\n🎯 === FORMATO EXATO DO EXEMPLO (ID) ===")
        
        # Replicar exatamente o exemplo fornecido, adaptado para OS
        params = {
            'qtype': 'su_oss_chamado.id',          # campo de filtro
            'query': '15350',                       # valor para consultar  
            'oper': '=',                           # operador da consulta
            'page': '1',                           # página a ser mostrada
            'rp': '1',                            # quantidade de registros por página
            'sortname': 'su_oss_chamado.id',       # campo para ordenar a consulta
            'sortorder': 'desc'                    # ordenação (asc= crescente | desc=decrescente)
        }
        
        response = requests.post(client.base_url, data=params, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total_especifico = int(data.get('total', 0))
            registros = data.get('registros', [])
            
            print(f"Total com ID=15350: {total_especifico}")
            
            if total_especifico == 1:
                print(f"✅ FILTRO FUNCIONOU! Encontrou exatamente 1 registro")
                if registros:
                    os_encontrada = registros[0]
                    print(f"   ID: {os_encontrada.get('id')}")
                    print(f"   Protocolo: {os_encontrada.get('protocolo')}")
                    print(f"   Data: {os_encontrada.get('data_abertura')}")
            elif total_especifico == 0:
                print(f"⚠️ Nenhuma OS com ID 15350 encontrada")
            else:
                print(f"⚠️ Resultado inesperado: {total_especifico} registros")
        
        # 3. TESTE COM OPERADORES DIFERENTES
        print(f"\n📊 === TESTANDO OPERADORES DIFERENTES ===")
        
        operadores_teste = [
            ('15000', '>=', 'ID maior ou igual 15000'),
            ('15300', '>', 'ID maior que 15300'),
            ('15400', '<', 'ID menor que 15400'),
            ('15350', '=', 'ID igual a 15350'),
            ('15351', '=', 'ID igual a 15351'),
        ]
        
        for valor, oper, descricao in operadores_teste:
            params_op = {
                'qtype': 'su_oss_chamado.id',
                'query': valor,
                'oper': oper,
                'page': '1',
                'rp': '5',
                'sortname': 'su_oss_chamado.id',
                'sortorder': 'desc'
            }
            
            response = requests.post(client.base_url, data=params_op, headers=headers, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                total = int(data.get('total', 0))
                
                print(f"   {descricao}: {total} OS")
                
                if total != total_original:
                    print(f"      ✅ OPERADOR {oper} FUNCIONOU! ({total_original} -> {total})")
                    
                    # Se funcionou, mostrar alguns exemplos
                    registros = data.get('registros', [])
                    for i, reg in enumerate(registros[:3], 1):
                        id_os = reg.get('id')
                        print(f"         {i}. ID {id_os}")
        
        # 4. TESTE COM DATA (formato exato)
        print(f"\n📅 === TESTE COM DATA (FORMATO EXATO) ===")
        
        formatos_data = [
            ('2025-11-22', '=', 'Data igual'),
            ('2025-11-22', 'like', 'Data contém'),
            ('2025-11', 'like', 'Mês/ano contém'),
            ('2025-11-01', '>=', 'Data maior igual'),
        ]
        
        for valor_data, oper_data, desc_data in formatos_data:
            params_data = {
                'qtype': 'su_oss_chamado.data_abertura',
                'query': valor_data,
                'oper': oper_data,
                'page': '1',
                'rp': '5',
                'sortname': 'su_oss_chamado.id', 
                'sortorder': 'desc'
            }
            
            response = requests.post(client.base_url, data=params_data, headers=headers, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                total_data = int(data.get('total', 0))
                
                print(f"   {desc_data} '{valor_data}': {total_data} OS")
                
                if total_data != total_original and total_data > 0:
                    print(f"      ✅ FILTRO DATA FUNCIONOU!")
                    
                    registros = data.get('registros', [])
                    for i, reg in enumerate(registros[:3], 1):
                        id_os = reg.get('id')
                        data_ab = reg.get('data_abertura')
                        print(f"         {i}. ID {id_os} - {data_ab}")
        
        # 5. VERIFICAR SE É PROBLEMA DE HEADERS
        print(f"\n🔧 === TESTE COM HEADERS DIFERENTES ===")
        
        headers_alternativo = {
            'Authorization': client.headers['Authorization'],
            'Content-Type': 'application/x-www-form-urlencoded',  # Mudança aqui
            'ixcsoft': 'listar'
        }
        
        params_header_test = {
            'qtype': 'su_oss_chamado.id',
            'query': '15300',
            'oper': '>=',
            'page': '1',
            'rp': '10',
            'sortname': 'su_oss_chamado.id',
            'sortorder': 'desc'
        }
        
        response = requests.post(client.base_url, data=params_header_test, headers=headers_alternativo, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total_alt = int(data.get('total', 0))
            print(f"Com header alternativo: {total_alt} OS")
            
            if total_alt != total_original:
                print(f"✅ HEADER ALTERNATIVO FUNCIONOU!")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_api_call():
    """Testa chamada manual para API para debug"""
    print(f"\n🔬 === DEBUG MANUAL DA API ===")
    
    try:
        import requests
        import base64
        from olt.client_utils import IxcOSClient
        
        client = IxcOSClient()
        
        print(f"Host: {client.host}")
        print(f"Base URL: {client.base_url}")
        print(f"Headers: {client.headers}")
        
        # Chamada mais simples possível
        payload_debug = {
            'page': '1',
            'rp': '5'
        }
        
        headers_debug = {
            'Authorization': client.headers['Authorization'],
            'ixcsoft': 'listar'
        }
        
        print(f"\\n📡 Fazendo chamada básica...")
        response = requests.post(client.base_url, data=payload_debug, headers=headers_debug, verify=False)
        
        print(f"Status: {response.status_code}")
        print(f"Headers resposta: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total: {data.get('total', 'N/A')}")
            print(f"Registros: {len(data.get('registros', []))}")
            
            registros = data.get('registros', [])
            if registros:
                primeiro = registros[0]
                print(f"Primeiro registro ID: {primeiro.get('id')}")
                print(f"Campos disponíveis: {list(primeiro.keys())[:10]}")
        else:
            print(f"Erro: {response.text[:200]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == '__main__':
    print("🔬 TESTE FORMATO EXATO BASEADO NO EXEMPLO IXC")
    
    test_exact_format()
    test_manual_api_call()
    
    print("\\n🏁 TESTE CONCLUÍDO")