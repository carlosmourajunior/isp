#!/usr/bin/env python3
"""
Script para testar o endpoint de ONUs por PON específica
GET /api/onus/pon/{pon}/
"""

import requests
import json
import sys
import urllib.parse

def test_onus_by_pon_endpoint():
    # Configuração
    base_url = "http://localhost:8000/api"
    
    # Credenciais
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
        
        # 3. Testar com diferentes PONs
        test_pons = ["1/1/1/1", "1/1/2/9", "1/1/1/14", "1/1/1/10"]
        
        for pon in test_pons:
            print(f"\n📡 Testando PON: {pon}")
            print("="*60)
            
            # Codificar a PON para URL (importante para caracteres especiais como /)
            encoded_pon = urllib.parse.quote(pon, safe='')
            url = f"{base_url}/onus/pon/{encoded_pon}/"
            
            print(f"🌐 URL: {url}")
            
            # Fazer requisição para o endpoint
            pon_response = requests.get(url, headers=headers)
            
            if pon_response.status_code == 200:
                pon_data = pon_response.json()
                
                print(f"✅ Sucesso! Status: {pon_response.status_code}")
                print(f"📊 Total de ONUs na PON {pon}: {pon_data.get('count', 0)}")
                
                # A resposta agora tem estrutura de paginação
                results = pon_data.get('results', [])
                if isinstance(results, dict) and 'results' in results:
                    # Resposta tem estrutura aninhada devido à paginação customizada
                    onus_list = results['results']
                    total_count = results.get('total_onus', pon_data.get('count', 0))
                elif isinstance(results, list):
                    # Lista direta de ONUs
                    onus_list = results
                    total_count = pon_data.get('count', len(results))
                else:
                    onus_list = []
                    total_count = 0
                
                if onus_list:
                    print(f"📋 Primeiras ONUs encontradas:")
                    
                    for i, onu in enumerate(onus_list[:5]):  # Mostrar apenas as 5 primeiras
                        print(f"   {i+1}. ID: {onu.get('id')} | Serial: {onu.get('serial')} | Estado: {onu.get('oper_state')} | Cliente: {onu.get('desc1', 'N/A')}")
                    
                    if total_count > 5:
                        print(f"   ... e mais {total_count - 5} ONUs")
                    
                    # Verificar paginação
                    if pon_data.get('next'):
                        print(f"🔗 Próxima página: {pon_data['next']}")
                    if pon_data.get('previous'):
                        print(f"🔗 Página anterior: {pon_data['previous']}")
                    
                    # Mostrar estatísticas por estado
                    onus = pon_data['results']
                    estados = {}
                    for onu in onus:
                        estado = onu.get('oper_state', 'unknown')
                        estados[estado] = estados.get(estado, 0) + 1
                    
                    print(f"📈 Estados das ONUs (amostra):")
                    for estado, count in estados.items():
                        print(f"   • {estado}: {count}")
                
                else:
                    print(f"ℹ️  Nenhuma ONU encontrada na PON {pon}")
                
            else:
                print(f"❌ Erro: Status {pon_response.status_code}")
                print(f"Resposta: {pon_response.text}")
            
            # Parar após o primeiro sucesso para não poluir a saída
            if pon_response.status_code == 200 and pon_data.get('count', 0) > 0:
                break
        
        # 4. Testar com PON inexistente
        print(f"\n🔍 Testando com PON inexistente (99/99/99/99)...")
        print("="*60)
        
        invalid_pon = "99/99/99/99"
        encoded_invalid_pon = urllib.parse.quote(invalid_pon, safe='')
        invalid_url = f"{base_url}/onus/pon/{encoded_invalid_pon}/"
        
        invalid_response = requests.get(invalid_url, headers=headers)
        print(f"Status: {invalid_response.status_code}")
        
        if invalid_response.status_code == 200:
            invalid_data = invalid_response.json()
            if invalid_data.get('count', 0) == 0:
                print("✅ Comportamento correto: Lista vazia para PON inexistente")
            else:
                print(f"⚠️  Encontrou {invalid_data['count']} ONUs na PON inexistente")
        else:
            print(f"Status inesperado: {invalid_response.status_code}")
        
        print(f"Resposta: {invalid_response.text}")
        
        # 5. Testar filtros adicionais (se suportados)
        print(f"\n🎯 Testando filtros adicionais na PON 1/1/1/1...")
        print("="*60)
        
        # Testar filtro por estado operacional
        encoded_test_pon = urllib.parse.quote("1/1/1/1", safe='')
        filter_url = f"{base_url}/onus/pon/{encoded_test_pon}/?oper_state=up"
        
        filter_response = requests.get(filter_url, headers=headers)
        if filter_response.status_code == 200:
            filter_data = filter_response.json()
            print(f"✅ ONUs UP na PON 1/1/1/1: {filter_data.get('count', 0)}")
        else:
            print(f"⚠️  Filtro por estado não suportado: {filter_response.status_code}")
        
        # 6. Testar sem autenticação
        print(f"\n🚫 Testando sem token de autenticação...")
        print("="*60)
        
        no_auth_response = requests.get(f"{base_url}/onus/pon/1%2F1%2F1%2F1/")
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

def show_url_encoding_examples():
    """Mostra exemplos de codificação de URL para PONs"""
    print("\n📚 Exemplos de codificação de URL para PONs:")
    print("="*60)
    
    pons_examples = [
        "1/1/1/1",
        "gpon-olt_1/1/1/1", 
        "1/1/2/16",
        "slot_1/port_2"
    ]
    
    for pon in pons_examples:
        encoded = urllib.parse.quote(pon, safe='')
        print(f"PON: '{pon}' → URL encoded: '{encoded}'")
    
    print("\n💡 Dica: Use urllib.parse.quote() em Python para codificar PONs com caracteres especiais")

if __name__ == "__main__":
    test_onus_by_pon_endpoint()
    show_url_encoding_examples()