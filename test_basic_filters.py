#!/usr/bin/env python
"""
Script simples para testar se filtros de ID funcionam
e descobrir a estrutura correta
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_basic_filters():
    """Teste básico com filtros simples"""
    print("=== TESTE BÁSICO DE FILTROS ===")
    
    try:
        from olt.client_utils import IxcOSClient
        import requests
        
        client = IxcOSClient()
        headers = client.headers.copy()
        headers['ixcsoft'] = 'listar'
        
        # 1. Teste base - sem filtros
        print(f"\n1. SEM FILTROS:")
        payload_base = {
            'qtype': 'su_oss_chamado.id',
            'query': '0',
            'oper': '>',
            'page': '1',
            'rp': '10'
        }
        
        response = requests.post(client.base_url, data=payload_base, headers=headers, verify=False)
        total_base = response.json().get('total', 0) if response.status_code == 200 else 0
        print(f"   Total: {total_base}")
        
        # 2. Teste com ID > 15000 (deveria reduzir significativamente)
        print(f"\n2. ID > 15000:")
        payload_id = {
            'qtype': 'su_oss_chamado.id',
            'query': '15000',
            'oper': '>',
            'page': '1',
            'rp': '10'
        }
        
        response = requests.post(client.base_url, data=payload_id, headers=headers, verify=False)
        total_id = response.json().get('total', 0) if response.status_code == 200 else 0
        print(f"   Total: {total_id}")
        
        if total_id < total_base and total_id > 0:
            print(f"   ✅ FILTRO DE ID FUNCIONOU! ({total_base} -> {total_id})")
            
            # 3. Se ID funciona, testar ranges específicos
            print(f"\n3. TESTANDO RANGES DE ID:")
            
            ranges = [
                (15300, '>'),
                (15350, '>='),
                (15320, '<='),
                (15306, '>='),  # Início do range que falta
                (15327, '<='),  # Fim do range que falta
            ]
            
            for valor, operador in ranges:
                payload_range = payload_base.copy()
                payload_range.update({
                    'query': str(valor),
                    'oper': operador
                })
                
                response = requests.post(client.base_url, data=payload_range, headers=headers, verify=False)
                total_range = response.json().get('total', 0) if response.status_code == 200 else 0
                print(f"   ID {operador} {valor}: {total_range} OS")
            
            # 4. Teste específico para range 15306-15327 (nossos IDs faltantes)
            print(f"\n4. TESTE RANGE ESPECÍFICO 15306-15327:")
            
            # Método 1: Duas consultas separadas (>= 15306 E <= 15327)
            payload_inicio = payload_base.copy()
            payload_inicio.update({
                'query': '15306',
                'oper': '>='
            })
            
            response = requests.post(client.base_url, data=payload_inicio, headers=headers, verify=False)
            if response.status_code == 200:
                data = response.json()
                registros = data.get('registros', [])
                
                os_no_range = []
                for reg in registros:
                    id_os = int(reg.get('id', 0))
                    if 15306 <= id_os <= 15327:
                        os_no_range.append({
                            'id': id_os,
                            'protocolo': reg.get('protocolo'),
                            'data_abertura': reg.get('data_abertura'),
                            'status': reg.get('status')
                        })
                
                print(f"   OS no range 15306-15327: {len(os_no_range)}")
                for os in os_no_range:
                    print(f"      ID {os['id']}: {os['protocolo']} - {os['data_abertura']} - {os['status']}")
        
        else:
            print(f"   ❌ Filtro ID não funcionou")
            
            # Se nem ID funciona, talvez seja problema de endpoint ou método
            print(f"\n⚠️ TENTANDO MÉTODO ALTERNATIVO:")
            
            # Tentar sem qtype/query/oper
            payload_alt = {
                'page': '1', 
                'rp': '10',
                'id': '>15000'  # Filtro direto
            }
            
            response = requests.post(client.base_url, data=payload_alt, headers=headers, verify=False)
            if response.status_code == 200:
                total_alt = response.json().get('total', 0)
                print(f"   Método alternativo: {total_alt}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

def sync_specific_range():
    """Sincroniza range específico se filtros funcionarem"""
    print(f"\n🎯 === SINCRONIZAÇÃO RANGE ESPECÍFICO ===")
    
    try:
        from olt.client_utils import IxcOSClient
        from olt.models import OrdemServicoIxc
        
        # IDs que sabemos que faltam
        ids_faltantes = list(range(15306, 15328))  # 15306 até 15327
        
        print(f"IDs a sincronizar: {ids_faltantes}")
        
        client = IxcOSClient()
        
        novas_os = 0
        for id_os in ids_faltantes:
            # Verificar se já existe no banco
            if OrdemServicoIxc.objects.filter(id=id_os).exists():
                print(f"   ID {id_os}: já existe no banco")
                continue
            
            # Tentar buscar na API
            try:
                os_data = client.buscar_os_por_id(id_os)
                if os_data:
                    print(f"   ✅ ID {id_os}: encontrada na API")
                    novas_os += 1
                else:
                    print(f"   ❌ ID {id_os}: não encontrada na API")
            except Exception as e:
                print(f"   ❌ ID {id_os}: erro - {e}")
        
        print(f"\n📊 Resultado: {novas_os} novas OS encontradas")
        return True
        
    except Exception as e:
        print(f"❌ Erro na sincronização: {e}")
        return False

if __name__ == '__main__':
    print("🧪 TESTE FILTROS BÁSICOS")
    
    if test_basic_filters():
        sync_specific_range()
    
    print("\n🏁 TESTE CONCLUÍDO")