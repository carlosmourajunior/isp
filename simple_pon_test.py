#!/usr/bin/env python3
"""
Teste simples do endpoint de ONUs por PON específica
GET /api/onus/pon/{pon}/
"""

import requests
import json

def simple_test():
    base_url = "http://localhost:8000/api"
    
    # 1. Login
    login_data = {"username": "testapi", "password": "testapi123"}
    login_response = requests.post(f"{base_url}/auth/login/", json=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Erro no login: {login_response.status_code}")
        return
    
    access_token = login_response.json()['access']
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("✅ Login realizado com sucesso!")
    
    # 2. Testar endpoint com PON que tem ONUs
    pon = "1/1/1/1"
    response = requests.get(f"{base_url}/onus/pon/{pon}/", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"🎯 Testando PON: {pon}")
        print(f"📊 Status: {response.status_code}")
        print(f"📈 Total de ONUs: {data.get('count', 'N/A')}")
        
        # Verificar estrutura da resposta
        if 'results' in data:
            results = data['results']
            if isinstance(results, dict):
                onus_list = results.get('results', [])
                print(f"📋 ONUs encontradas: {len(onus_list)}")
                if onus_list:
                    print("🔍 Primeira ONU:")
                    onu = onus_list[0]
                    print(f"   - ID: {onu.get('id')}")
                    print(f"   - Serial: {onu.get('serial')}")
                    print(f"   - Estado: {onu.get('oper_state')}")
                    print(f"   - Cliente: {onu.get('desc1')}")
        
        # Mostrar resposta JSON formatada (primeiras linhas)
        print(f"\n📄 Estrutura da resposta:")
        response_str = json.dumps(data, indent=2, ensure_ascii=False)
        lines = response_str.split('\n')[:15]  # Primeiras 15 linhas
        for line in lines:
            print(line)
        if len(response_str.split('\n')) > 15:
            print("  ...")
    
    else:
        print(f"❌ Erro: {response.status_code}")
        print(f"Resposta: {response.text}")

    # 3. Testar filtros
    print(f"\n🎯 Testando filtros - ONUs UP na PON {pon}:")
    filter_response = requests.get(f"{base_url}/onus/pon/{pon}/?oper_state=up", headers=headers)
    
    if filter_response.status_code == 200:
        filter_data = filter_response.json()
        print(f"✅ ONUs UP: {filter_data.get('count', 'N/A')}")
    else:
        print(f"❌ Erro nos filtros: {filter_response.status_code}")

if __name__ == "__main__":
    simple_test()