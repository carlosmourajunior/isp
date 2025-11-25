#!/usr/bin/env python
"""
Script para testar a estrutura correta da API IXC baseado na documentação oficial
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_ixc_api_docs_structure():
    """Testa estrutura baseada na documentação oficial do IXC"""
    print("=== TESTE BASEADO NA DOCUMENTAÇÃO IXC ===")
    
    try:
        from olt.client_utils import IxcOSClient
        import requests
        
        client = IxcOSClient()
        headers = client.headers.copy()
        headers['ixcsoft'] = 'listar'
        
        print(f"🔗 Base URL: {client.base_url}")
        print(f"🔑 Headers: {headers}")
        
        # 1. PRIMEIRO: Validar se a API responde corretamente
        print(f"\n📡 === VALIDAÇÃO BÁSICA DA API ===")
        
        payload_basico = {
            'qtype': 'su_oss_chamado.id',
            'query': '0', 
            'oper': '>',
            'page': '1',
            'rp': '5',
            'sortname': 'su_oss_chamado.id',
            'sortorder': 'desc'
        }
        
        response = requests.post(client.base_url, data=payload_basico, headers=headers, verify=False)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Erro na API: {response.text[:200]}")
            return False
        
        data = response.json()
        total_registros = int(data.get('total', 0))
        registros = data.get('registros', [])
        
        print(f"✅ API respondeu: {total_registros} registros totais")
        print(f"✅ Registros retornados: {len(registros)}")
        
        # 2. ANÁLISE DOS CAMPOS DISPONÍVEIS
        if registros:
            primeiro = registros[0]
            print(f"\n📋 === CAMPOS DISPONÍVEIS ===")
            campos_importantes = ['id', 'protocolo', 'data_abertura', 'status', 'tipo']
            
            for campo in campos_importantes:
                valor = primeiro.get(campo, 'N/A')
                print(f"   {campo}: {valor}")
        
        # 3. TESTE DE FILTROS SEGUNDO DOCUMENTAÇÃO IXC
        # Baseado no padrão comum de APIs IXC que vi na documentação
        print(f"\n🔍 === TESTANDO FILTROS DOCUMENTAÇÃO IXC ===")
        
        # Estrutura 1: Filtro por range de data (formato comum IXC)
        print(f"\n1. Filtro de Data (range):")
        payload_data_range = {
            'qtype': 'su_oss_chamado.data_abertura',
            'query': '2025-11-22',
            'oper': 'like',  # Muitas APIs IXC usam 'like' para datas
            'page': '1',
            'rp': '10'
        }
        
        response = requests.post(client.base_url, data=payload_data_range, headers=headers, verify=False)
        if response.status_code == 200:
            total_data = response.json().get('total', 0)
            print(f"   Data like '2025-11-22': {total_data} registros")
        
        # Estrutura 2: Filtro por ID específico (deve funcionar)
        print(f"\n2. Filtro de ID específico:")
        payload_id_especifico = {
            'qtype': 'su_oss_chamado.id',
            'query': '15350',
            'oper': '=',
            'page': '1',
            'rp': '1'
        }
        
        response = requests.post(client.base_url, data=payload_id_especifico, headers=headers, verify=False)
        if response.status_code == 200:
            data_id = response.json()
            total_id = data_id.get('total', 0)
            registros_id = data_id.get('registros', [])
            
            print(f"   ID = 15350: {total_id} registros")
            
            if registros_id:
                os_encontrada = registros_id[0]
                print(f"   ✅ OS encontrada: {os_encontrada.get('protocolo')} - {os_encontrada.get('data_abertura')}")
        
        # Estrutura 3: Múltiplos filtros (arrays) - padrão IXC
        print(f"\n3. Múltiplos filtros (formato IXC):")
        
        # Tentar formato com arrays (comum em APIs IXC)
        import urllib.parse
        
        data_multiplos = {
            'page': '1',
            'rp': '10',
            'qtype': 'su_oss_chamado.id',
            'query': '15300',
            'oper': '>='
        }
        
        response = requests.post(client.base_url, data=data_multiplos, headers=headers, verify=False)
        if response.status_code == 200:
            total_multi = response.json().get('total', 0)
            print(f"   ID >= 15300: {total_multi} registros")
            
            if total_multi != total_registros:
                print(f"   ✅ FILTRO FUNCIONOU! ({total_registros} -> {total_multi})")
                return test_working_filters(client, headers)
        
        # Estrutura 4: Filtros por período específico
        print(f"\n4. Filtro por período (nov/2025):")
        
        # Testar diferentes formatos de data que IXC pode aceitar
        formatos_data = [
            ('2025-11', 'like'),          # Mês/ano
            ('2025-11-22', '>='),         # Data específica maior igual  
            ('22/11/2025', 'like'),       # Formato brasileiro
            ('2025-11-01', '>='),         # Início do período
        ]
        
        for formato, operador in formatos_data:
            payload_periodo = {
                'qtype': 'su_oss_chamado.data_abertura',
                'query': formato,
                'oper': operador,
                'page': '1',
                'rp': '10'
            }
            
            response = requests.post(client.base_url, data=payload_periodo, headers=headers, verify=False)
            if response.status_code == 200:
                total_periodo = response.json().get('total', 0)
                print(f"   Data {operador} '{formato}': {total_periodo}")
                
                if total_periodo != total_registros and total_periodo > 0:
                    print(f"   ✅ FORMATO FUNCIONOU: {formato} com {operador}")
        
        return False  # Se chegou aqui, nenhum filtro funcionou
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_working_filters(client, headers):
    """Testa filtros que funcionam para encontrar as 56 OS"""
    print(f"\n🎯 === TESTANDO FILTROS QUE FUNCIONAM ===")
    
    try:
        # Se chegamos aqui, o filtro ID >= 15300 funcionou
        # Vamos refinar para encontrar as OS do período
        
        # 1. Testar range de IDs que corresponde ao período
        print(f"\n📊 Análise por ranges de ID:")
        
        ranges_teste = [
            (15000, '>='),
            (15100, '>='),  
            (15200, '>='),
            (15300, '>='),
            (15350, '<='),
        ]
        
        for id_val, oper in ranges_teste:
            payload = {
                'qtype': 'su_oss_chamado.id', 
                'query': str(id_val),
                'oper': oper,
                'page': '1',
                'rp': '10'
            }
            
            response = requests.post(client.base_url, data=payload, headers=headers, verify=False)
            if response.status_code == 200:
                total = response.json().get('total', 0)
                print(f"   ID {oper} {id_val}: {total} OS")
        
        # 2. Range específico onde estão nossas 56 OS  
        print(f"\n🔍 Buscando OS no range 15295-15352:")
        
        payload_range = {
            'qtype': 'su_oss_chamado.id',
            'query': '15295', 
            'oper': '>=',
            'page': '1',
            'rp': '100'  # Buscar até 100 registros
        }
        
        response = requests.post(client.base_url, data=payload_range, headers=headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            registros = data.get('registros', [])
            
            # Filtrar apenas OS do range que nos interessa
            os_do_periodo = []
            for reg in registros:
                id_os = int(reg.get('id', 0))
                if id_os >= 15295 and id_os <= 15352:
                    data_abertura = reg.get('data_abertura', '')
                    # Verificar se é de novembro 2025
                    if '2025-11-' in data_abertura:
                        os_do_periodo.append({
                            'id': id_os,
                            'protocolo': reg.get('protocolo'),
                            'data_abertura': data_abertura,
                            'status': reg.get('status'),
                            'tipo': reg.get('tipo')
                        })
            
            print(f"✅ OS de novembro/2025 encontradas: {len(os_do_periodo)}")
            
            if len(os_do_periodo) >= 56:
                print(f"🎉 ENCONTRAMOS AS 56+ OS!")
                
                print(f"\nPrimeiras 10 OS encontradas:")
                for i, os in enumerate(os_do_periodo[:10], 1):
                    print(f"   {i}. ID {os['id']} - {os['protocolo']} - {os['data_abertura']} - {os['status']}/{os['tipo']}")
                
                # Verificar quais não estão no banco
                from olt.models import OrdemServicoIxc
                
                ids_nao_no_banco = []
                for os in os_do_periodo:
                    if not OrdemServicoIxc.objects.filter(id_ixc=os['id']).exists():
                        ids_nao_no_banco.append(os['id'])
                
                print(f"\n📋 IDs não no banco: {len(ids_nao_no_banco)}")
                if ids_nao_no_banco:
                    print(f"   Faltando: {sorted(ids_nao_no_banco)}")
                
                return os_do_periodo
            else:
                print(f"⚠️ Apenas {len(os_do_periodo)} OS encontradas (esperado: 56)")
        
        return []
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

def sync_found_os(os_list):
    """Sincroniza as OS encontradas que estão faltando"""
    print(f"\n🚀 === SINCRONIZANDO OS FALTANTES ===")
    
    try:
        from olt.client_utils import IxcOSClient
        from olt.models import OrdemServicoIxc
        
        client = IxcOSClient()
        
        # Encontrar IDs que não estão no banco
        ids_faltando = []
        for os in os_list:
            id_ixc = os['id']
            if not OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists():
                ids_faltando.append(id_ixc)
        
        print(f"IDs para sincronizar: {len(ids_faltando)}")
        
        if not ids_faltando:
            print("✅ Todas as OS já estão sincronizadas!")
            return True
        
        # Sincronizar uma por vez para garantir
        sincronizadas = 0
        for id_ixc in ids_faltando[:10]:  # Máximo 10 por vez para teste
            try:
                # Buscar OS específica na API
                os_data = client.buscar_os_por_id(id_ixc)
                if os_data:
                    print(f"   ✅ Sincronizada: ID {id_ixc}")
                    sincronizadas += 1
                else:
                    print(f"   ❌ Erro ao sincronizar: ID {id_ixc}")
            except Exception as e:
                print(f"   ❌ Erro ID {id_ixc}: {e}")
        
        print(f"\n📊 Resultado: {sincronizadas} OS sincronizadas")
        
        # Verificar total final
        total_final = OrdemServicoIxc.objects.count()
        periodo_count = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte='2025-11-01',
            data_abertura__date__lte='2025-11-24'
        ).count()
        
        print(f"Total OS no banco: {total_final}")
        print(f"OS do período nov: {periodo_count}")
        
        if periodo_count >= 56:
            print(f"🎉 META ATINGIDA! {periodo_count} OS do período")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na sincronização: {e}")
        return False

if __name__ == '__main__':
    print("📚 TESTE BASEADO NA DOCUMENTAÇÃO IXC")
    
    sucesso = test_ixc_api_docs_structure()
    
    if isinstance(sucesso, list) and len(sucesso) > 0:
        print(f"\n🎯 OS encontradas: {len(sucesso)}")
        
        confirma = input("Sincronizar OS faltantes? (s/N): ").strip().lower()
        if confirma == 's':
            sync_found_os(sucesso)
    
    print("\n🏁 TESTE CONCLUÍDO")