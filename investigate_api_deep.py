#!/usr/bin/env python
"""
Script para investigar estrutura real da API IXC
e descobrir como os filtros realmente funcionam
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def investigate_api_structure():
    """Investiga como a API realmente funciona"""
    print("=== INVESTIGAÇÃO DETALHADA DA API IXC ===")
    
    try:
        from olt.client_utils import IxcOSClient
        import requests
        import json
        
        client = IxcOSClient()
        
        # 1. Capturar uma resposta completa para análise
        print("\n📋 === ANÁLISE ESTRUTURA RESPOSTA ===")
        
        payload = {
            'qtype': 'su_oss_chamado.id',
            'query': '0',
            'oper': '>',
            'page': '1',
            'rp': '3',  # Só 3 registros para análise
            'sortname': 'su_oss_chamado.id',
            'sortorder': 'desc'
        }
        
        headers = client.headers.copy()
        headers['ixcsoft'] = 'listar'
        
        response = requests.post(client.base_url, data=payload, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            registros = data.get('registros', [])
            
            print(f"✅ Resposta obtida. Total: {data.get('total', 0)}")
            
            if registros:
                primeiro_registro = registros[0]
                print(f"\n🔍 CAMPOS DISPONÍVEIS NO PRIMEIRO REGISTRO:")
                for campo, valor in primeiro_registro.items():
                    print(f"   {campo}: {valor}")
                
                # Verificar datas especificamente
                print(f"\n📅 ANÁLISE DE DATAS:")
                for reg in registros:
                    id_os = reg.get('id')
                    data_abertura = reg.get('data_abertura')
                    data_prevista = reg.get('data_prevista')
                    data_finalizacao = reg.get('data_finalizacao')
                    print(f"   OS {id_os}: Abertura={data_abertura}, Prevista={data_prevista}, Finalização={data_finalizacao}")
        else:
            print(f"❌ Erro: {response.status_code}")
            return False
        
        # 2. Testar diferentes estruturas de filtro
        print(f"\n🔧 === TESTE ESTRUTURAS DE FILTRO ===")
        
        # Estrutura 1: Usar qtype/query/oper para data
        print(f"\n1. Filtro via qtype (data_abertura):")
        payload1 = {
            'qtype': 'su_oss_chamado.data_abertura',
            'query': '2025-11-01',
            'oper': '>=',
            'page': '1',
            'rp': '10',
            'sortname': 'su_oss_chamado.id',
            'sortorder': 'desc'
        }
        
        response = requests.post(client.base_url, data=payload1, headers=headers, verify=False)
        if response.status_code == 200:
            total1 = response.json().get('total', 0)
            print(f"   Total: {total1}")
        else:
            print(f"   Erro: {response.status_code}")
        
        # Estrutura 2: Filtro de intervalo na query
        print(f"\n2. Filtro intervalo na query:")
        payload2 = {
            'qtype': 'su_oss_chamado.data_abertura',
            'query': '2025-11-01 TO 2025-11-24',
            'oper': 'between',
            'page': '1',
            'rp': '10',
            'sortname': 'su_oss_chamado.id',
            'sortorder': 'desc'
        }
        
        response = requests.post(client.base_url, data=payload2, headers=headers, verify=False)
        if response.status_code == 200:
            total2 = response.json().get('total', 0)
            print(f"   Total: {total2}")
        else:
            print(f"   Erro: {response.status_code}")
        
        # Estrutura 3: Múltiplos filtros
        print(f"\n3. Múltiplos filtros (arrays):")
        payload3 = {
            'page': '1',
            'rp': '10',
            'sortname': 'su_oss_chamado.id',
            'sortorder': 'desc',
            'qtype[]': ['su_oss_chamado.data_abertura', 'su_oss_chamado.status'],
            'query[]': ['2025-11-01', 'A'],
            'oper[]': ['>=', '=']
        }
        
        response = requests.post(client.base_url, data=payload3, headers=headers, verify=False)
        if response.status_code == 200:
            total3 = response.json().get('total', 0)
            print(f"   Total: {total3}")
        else:
            print(f"   Erro: {response.status_code}")
        
        # Estrutura 4: Filtros com nomes diferentes
        print(f"\n4. Testando nomes de filtros alternativos:")
        
        filtros_teste = [
            ('filtro_data_abertura', '2025-11-01'),
            ('data_abertura_inicio', '2025-11-01'),
            ('data_abertura_fim', '2025-11-24'),
            ('filtro_status', 'A'),
            ('status_filtro', 'A'),
            ('su_oss_chamado_data_abertura', '2025-11-01'),
        ]
        
        for nome_filtro, valor in filtros_teste:
            payload_alt = {
                'qtype': 'su_oss_chamado.id',
                'query': '0',
                'oper': '>',
                'page': '1',
                'rp': '5',
                nome_filtro: valor
            }
            
            response = requests.post(client.base_url, data=payload_alt, headers=headers, verify=False)
            if response.status_code == 200:
                total_alt = response.json().get('total', 0)
                if total_alt != 14815:  # Se diferente do total, funcionou
                    print(f"   ✅ {nome_filtro}: {total_alt} (FUNCIONOU!)")
                else:
                    print(f"   ❌ {nome_filtro}: {total_alt}")
        
        # 5. Análise de uma OS específica que sabemos existir
        print(f"\n🎯 === TESTE COM OS ESPECÍFICA ===")
        
        # Buscar uma OS que sabemos que existe (das últimas)
        payload_especifica = {
            'qtype': 'su_oss_chamado.id',
            'query': '15350',
            'oper': '=',
            'page': '1',
            'rp': '1'
        }
        
        response = requests.post(client.base_url, data=payload_especifica, headers=headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            total_esp = data.get('total', 0)
            registros = data.get('registros', [])
            
            print(f"Busca por OS 15350: {total_esp} registros")
            
            if registros:
                os_detalhes = registros[0]
                data_abertura = os_detalhes.get('data_abertura')
                print(f"Data abertura: {data_abertura}")
                
                # Agora tentar filtrar por essa data exata
                if data_abertura:
                    data_parte = data_abertura.split()[0]  # Pegar só a parte da data
                    
                    payload_data_exata = {
                        'qtype': 'su_oss_chamado.data_abertura',
                        'query': data_parte,
                        'oper': 'like',
                        'page': '1',
                        'rp': '10'
                    }
                    
                    response = requests.post(client.base_url, data=payload_data_exata, headers=headers, verify=False)
                    if response.status_code == 200:
                        total_data_exata = response.json().get('total', 0)
                        print(f"OS com data {data_parte}: {total_data_exata}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_filter_combinations():
    """Testa diferentes combinações de filtros"""
    print(f"\n🧪 === TESTE COMBINAÇÕES DE FILTROS ===")
    
    try:
        from olt.client_utils import IxcOSClient
        import requests
        
        client = IxcOSClient()
        headers = client.headers.copy()
        headers['ixcsoft'] = 'listar'
        
        # Base payload
        base = {
            'page': '1',
            'rp': '5',
            'sortname': 'su_oss_chamado.id',
            'sortorder': 'desc'
        }
        
        # Testes com diferentes operadores
        operadores_teste = [
            ('=', 'igual'),
            ('>=', 'maior igual'),
            ('>', 'maior'),
            ('<=', 'menor igual'), 
            ('<', 'menor'),
            ('like', 'contém'),
            ('!=', 'diferente')
        ]
        
        for oper, desc in operadores_teste:
            payload = base.copy()
            payload.update({
                'qtype': 'su_oss_chamado.status',
                'query': 'A',
                'oper': oper
            })
            
            response = requests.post(client.base_url, data=payload, headers=headers, verify=False)
            if response.status_code == 200:
                total = response.json().get('total', 0)
                if total != 14815:
                    print(f"   ✅ Status {oper} ({desc}): {total} OS")
                else:
                    print(f"   ❌ Status {oper} ({desc}): {total} OS")
        
        # Teste com IDs em diferentes ranges
        print(f"\n📊 Testando ranges de ID:")
        
        ranges_id = [
            (15300, '>'),
            (15350, '>'),
            (15320, '>='),
            (15330, '<='),
            (0, '>'),
        ]
        
        for id_val, oper in ranges_id:
            payload = base.copy()
            payload.update({
                'qtype': 'su_oss_chamado.id',
                'query': str(id_val),
                'oper': oper
            })
            
            response = requests.post(client.base_url, data=payload, headers=headers, verify=False)
            if response.status_code == 200:
                total = response.json().get('total', 0)
                print(f"   ID {oper} {id_val}: {total} OS")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == '__main__':
    print("🔬 INVESTIGAÇÃO PROFUNDA API IXC")
    
    investigate_api_structure()
    test_filter_combinations()
    
    print("\n🏁 INVESTIGAÇÃO CONCLUÍDA")