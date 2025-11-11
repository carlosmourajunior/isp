#!/usr/bin/env python3
"""
Script para testar o endpoint de detalhes de uma ONU específica
GET /api/onus/{id}/
"""

import requests
import json
import sys

def test_onu_detail_endpoint():
    # Configuração
    base_url = "http://localhost:8000/api"
    
    # Credenciais (ajustar conforme necessário)
    login_data = {
        "username": "testapi", 
        "password": "testapi123"
    }
    
    try:
        # 1. Fazer login para obter token
        print("🔐 Fazendo login...")
        login_response = requests.post(f"{base_url}/auth/login/", json=login_data)
        
        if login_response.status_code != 200:
            print(f"❌ Erro no login: {login_response.status_code}")
            print(f"Resposta: {login_response.text}")
            return
        
        tokens = login_response.json()
        access_token = tokens['access']
        print(f"✅ Login realizado com sucesso!")
        print(f"👤 Usuário: {tokens['user_info']['username']}")
        
        # 2. Configurar headers com token
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 3. Testar com diferentes IDs de ONUs
        test_ids = [11428, 11427, 11439, 11417, 11418]
        
        for onu_id in test_ids:
            print(f"\n📡 Testando ONU ID: {onu_id}")
            print("="*50)
            
            # Fazer requisição para o endpoint
            onu_response = requests.get(f"{base_url}/onus/{onu_id}/", headers=headers)
            
            if onu_response.status_code == 200:
                onu_data = onu_response.json()
                
                print(f"✅ Sucesso! Status: {onu_response.status_code}")
                print(f"📋 Detalhes da ONU:")
                print(f"   • ID: {onu_data.get('id')}")
                print(f"   • Serial: {onu_data.get('serial')}")
                print(f"   • PON: {onu_data.get('pon')}")
                print(f"   • Estado Operacional: {onu_data.get('oper_state')}")
                print(f"   • Estado Administrativo: {onu_data.get('admin_state')}")
                print(f"   • Sinal RX: {onu_data.get('olt_rx_sig')} dBm")
                print(f"   • Cliente Fibra: {onu_data.get('cliente_fibra')}")
                print(f"   • Descrição 1: {onu_data.get('desc1')}")
                print(f"   • Descrição 2: {onu_data.get('desc2')}")
                
                # Mostrar resposta JSON completa (formatada)
                print(f"\n📄 Resposta JSON completa:")
                print(json.dumps(onu_data, indent=2, ensure_ascii=False))
                
            else:
                print(f"❌ Erro: Status {onu_response.status_code}")
                print(f"Resposta: {onu_response.text}")
            
            # Parar após o primeiro sucesso para não poluir a saída
            if onu_response.status_code == 200:
                break
        
        # 4. Testar com ID inexistente
        print(f"\n🔍 Testando com ID inexistente (99999)...")
        print("="*50)
        
        invalid_response = requests.get(f"{base_url}/onus/99999/", headers=headers)
        print(f"Status: {invalid_response.status_code}")
        
        if invalid_response.status_code == 404:
            print("✅ Comportamento correto: 404 Not Found para ID inexistente")
        else:
            print(f"⚠️  Status inesperado: {invalid_response.status_code}")
            
        print(f"Resposta: {invalid_response.text}")
        
        # 5. Testar sem autenticação
        print(f"\n🚫 Testando sem token de autenticação...")
        print("="*50)
        
        no_auth_response = requests.get(f"{base_url}/onus/11428/")
        print(f"Status: {no_auth_response.status_code}")
        
        if no_auth_response.status_code == 401:
            print("✅ Comportamento correto: 401 Unauthorized sem token")
        else:
            print(f"⚠️  Status inesperado: {no_auth_response.status_code}")
            
        print(f"Resposta: {no_auth_response.text}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão: Verifique se o servidor está rodando em localhost:8000")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    test_onu_detail_endpoint()