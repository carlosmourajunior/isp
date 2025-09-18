#!/usr/bin/env python3
"""
Script de teste para a API OLT/ONT
Execute este script para testar os endpoints da API
"""

import requests
import json
import sys

# Configurações
BASE_URL = "http://localhost:8000"
USERNAME = "admin"  # Substitua pelo seu usuário
PASSWORD = "admin123"  # Substitua pela sua senha

def test_api():
    print("🔄 Testando API OLT/ONT...")
    
    # 1. Teste de autenticação
    print("\n1. Testando autenticação...")
    login_url = f"{BASE_URL}/api/auth/login/"
    login_data = {"username": USERNAME, "password": PASSWORD}
    
    try:
        response = requests.post(login_url, json=login_data)
        if response.status_code == 200:
            tokens = response.json()
            access_token = tokens['access']
            print("✅ Autenticação bem-sucedida!")
            print(f"   Token: {access_token[:50]}...")
        else:
            print(f"❌ Falha na autenticação: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão. Verifique se o servidor está rodando.")
        return False
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 2. Teste de listagem de ONUs
    print("\n2. Testando listagem de ONUs...")
    onus_url = f"{BASE_URL}/api/onus/"
    response = requests.get(onus_url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Listagem de ONUs bem-sucedida!")
        print(f"   Total de ONUs: {data.get('count', 0)}")
        if data.get('results'):
            print(f"   Primeira ONU: {data['results'][0].get('serial', 'N/A')}")
    else:
        print(f"❌ Falha na listagem de ONUs: {response.status_code}")
        print(f"   Resposta: {response.text}")
    
    # 3. Teste de estatísticas
    print("\n3. Testando estatísticas...")
    stats_url = f"{BASE_URL}/api/onus/stats/"
    response = requests.get(stats_url, headers=headers)
    
    if response.status_code == 200:
        stats = response.json()
        print("✅ Estatísticas obtidas com sucesso!")
        print(f"   Total de ONUs: {stats.get('total_onus', 0)}")
        print(f"   ONUs Online: {stats.get('onus_online', 0)}")
        print(f"   ONUs Offline: {stats.get('onus_offline', 0)}")
        print(f"   Percentual Online: {stats.get('percentual_online', 0)}%")
    else:
        print(f"❌ Falha ao obter estatísticas: {response.status_code}")
        print(f"   Resposta: {response.text}")
    
    # 4. Teste de busca
    print("\n4. Testando busca...")
    search_url = f"{BASE_URL}/api/onus/search/?q=FHTT"
    response = requests.get(search_url, headers=headers)
    
    if response.status_code == 200:
        search_data = response.json()
        print("✅ Busca realizada com sucesso!")
        print(f"   Resultados encontrados: {search_data.get('total_resultados', 0)}")
    else:
        print(f"❌ Falha na busca: {response.status_code}")
        print(f"   Resposta: {response.text}")
    
    # 5. Teste de filtros
    print("\n5. Testando filtros...")
    filter_url = f"{BASE_URL}/api/onus/?oper_state=up"
    response = requests.get(filter_url, headers=headers)
    
    if response.status_code == 200:
        filter_data = response.json()
        print("✅ Filtros funcionando!")
        print(f"   ONUs online: {filter_data.get('count', 0)}")
    else:
        print(f"❌ Falha nos filtros: {response.status_code}")
        print(f"   Resposta: {response.text}")
    
    print("\n🎉 Teste da API concluído!")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BASE_URL = sys.argv[1]
    
    print(f"Testando API em: {BASE_URL}")
    print(f"Usuário: {USERNAME}")
    print("=" * 50)
    
    success = test_api()
    sys.exit(0 if success else 1)