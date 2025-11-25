#!/usr/bin/env python
"""
Testa a API de assuntos do IXC para resolver o problema dos assuntos vazios
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_subjects_api():
    """Testa diferentes endpoints para obter assuntos"""
    print("=== TESTE DA API DE ASSUNTOS DO IXC ===")
    
    try:
        from olt.client_utils import IxcOSClient
        import requests
        
        client = IxcOSClient()
        
        # Tentar diferentes endpoints para assuntos
        endpoints_possiveis = [
            'su_assunto_os',
            'su_assunto',
            'assunto_os', 
            'assuntos',
            'su_categoria_assunto',
            'categoria_assunto'
        ]
        
        print("\n🔍 === TESTANDO ENDPOINTS DE ASSUNTOS ===")
        
        for endpoint in endpoints_possiveis:
            print(f"\n📡 Testando endpoint: {endpoint}")
            
            try:
                url = f"{client.base_url}/{endpoint}"
                headers = {'Authorization': f'Bearer {client.token}'}
                
                response = requests.get(
                    url,
                    headers=headers,
                    params={'qtype': 'su_assunto_os.id', 'query': '8'},
                    verify=False,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Sucesso! Status: {response.status_code}")
                    
                    if 'registros' in data:
                        registros = data['registros']
                        print(f"   📊 Encontrados {len(registros)} registros")
                        
                        if registros:
                            primeiro = registros[0]
                            print(f"   📋 Primeiro registro: {list(primeiro.keys())}")
                            
                            # Buscar assunto ID 8 especificamente  
                            for reg in registros:
                                if str(reg.get('id', '')) == '8':
                                    print(f"   🎯 ASSUNTO ID 8 ENCONTRADO:")
                                    for k, v in reg.items():
                                        print(f"       {k}: {v}")
                                    break
                    else:
                        print(f"   📄 Resposta direta: {str(data)[:200]}...")
                        
                elif response.status_code == 404:
                    print(f"   ❌ Endpoint não encontrado (404)")
                else:
                    print(f"   ⚠️ Status: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Erro: {e}")
        
        # Tentar busca específica no endpoint principal
        print(f"\n🎯 === BUSCA ESPECÍFICA POR ID_ASSUNTO = 8 ===")
        
        try:
            # Usar o endpoint que funcionou anteriormente  
            url = f"{client.base_url}/su_assunto_os"
            headers = {'Authorization': f'Bearer {client.token}'}
            
            # Diferentes formas de buscar
            params_list = [
                {'qtype': 'su_assunto_os.id', 'query': '8'},
                {'qtype': 'id', 'query': '8'},
                {'id': '8'},
                {'page': '1', 'rp': '50'}  # Listar todos
            ]
            
            for i, params in enumerate(params_list, 1):
                print(f"\n📡 Tentativa {i}: {params}")
                
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    verify=False,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Sucesso! Total: {data.get('total', 0)}")
                    
                    registros = data.get('registros', [])
                    for reg in registros:
                        reg_id = str(reg.get('id', ''))
                        nome = reg.get('assunto', reg.get('nome', reg.get('descricao', 'Sem nome')))
                        print(f"   ID {reg_id}: {nome}")
                        
                        if reg_id == '8':
                            print(f"   🎯 ASSUNTO 8 ENCONTRADO COMPLETO:")
                            for k, v in reg.items():
                                print(f"       {k}: {v}")
                else:
                    print(f"   ❌ Status: {response.status_code}")
                    
        except Exception as e:
            print(f"❌ Erro na busca específica: {e}")
        
        # Testar endpoint direto para ID 8
        print(f"\n🔗 === TESTE DE ENDPOINT DIRETO ===")
        
        try:
            url = f"{client.base_url}/su_assunto_os/8"
            headers = {'Authorization': f'Bearer {client.token}'}
            
            response = requests.get(url, headers=headers, verify=False, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Assunto ID 8 via endpoint direto:")
                if isinstance(data, dict):
                    for k, v in data.items():
                        print(f"   {k}: {v}")
                else:
                    print(f"   Dados: {data}")
            else:
                print(f"❌ Endpoint direto falhou: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erro no endpoint direto: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    sucesso = test_subjects_api()
    
    if sucesso:
        print("\n🎉 TESTE DE ASSUNTOS FINALIZADO!")
    else:
        print("\n❌ TESTE FALHOU")
        sys.exit(1)