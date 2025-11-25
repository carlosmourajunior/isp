#!/usr/bin/env python
"""
Script para testar filtros corretos da API do IXC
usando os campos disponíveis fornecidos pelo usuário
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_correct_filters():
    """Testa filtros usando os campos corretos da API"""
    print("=== TESTE DE FILTROS CORRETOS API IXC ===")
    
    try:
        from olt.client_utils import IxcOSClient
        import requests
        import base64
        from datetime import date
        
        client = IxcOSClient()
        
        # 1. Teste básico sem filtros
        print(f"\n🔍 === TESTE SEM FILTROS ===")
        
        payload_base = {
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
        
        response = requests.post(client.base_url, data=payload_base, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total_sem_filtro = int(data.get('total', 0))
            print(f"✅ Total sem filtros: {total_sem_filtro} OS")
        else:
            print(f"❌ Erro sem filtros: {response.status_code}")
            return False
        
        # 2. Teste com filtro de data usando campo direto
        print(f"\n📅 === TESTE COM FILTRO DE DATA DIRETA ===")
        
        payload_data_direta = payload_base.copy()
        payload_data_direta['data_abertura'] = '2025-11-01 - 2025-11-24'
        
        response = requests.post(client.base_url, data=payload_data_direta, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total_data_direta = int(data.get('total', 0))
            registros = data.get('registros', [])
            
            print(f"✅ Total com filtro data direta: {total_data_direta} OS")
            
            if total_data_direta < total_sem_filtro:
                print(f"🎉 FILTRO FUNCIONOU! Reduziu de {total_sem_filtro} para {total_data_direta}")
                
                print(f"📋 Primeiras OS filtradas:")
                for i, os in enumerate(registros[:5], 1):
                    id_os = os.get('id')
                    protocolo = os.get('protocolo', 'N/A')
                    data_abertura = os.get('data_abertura', 'N/A')
                    print(f"   {i}. ID {id_os} - {protocolo} - {data_abertura}")
            else:
                print(f"⚠️ Filtro pode não ter funcionado (mesmo total)")
        else:
            print(f"❌ Erro com filtro data: {response.status_code}")
        
        # 3. Teste com filtro de status
        print(f"\n📋 === TESTE COM FILTRO DE STATUS ===")
        
        payload_status = payload_base.copy()
        payload_status['status'] = 'A'  # Apenas abertas
        
        response = requests.post(client.base_url, data=payload_status, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total_abertas = int(data.get('total', 0))
            print(f"✅ OS abertas: {total_abertas}")
            
            if total_abertas != total_sem_filtro:
                print(f"✅ Filtro de status funcionou!")
        else:
            print(f"❌ Erro com filtro status: {response.status_code}")
        
        # 4. Teste com filtro de tipo
        print(f"\n🔧 === TESTE COM FILTRO DE TIPO ===")
        
        payload_tipo = payload_base.copy()
        payload_tipo['tipo'] = 'C'  # Corretiva
        
        response = requests.post(client.base_url, data=payload_tipo, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total_corretiva = int(data.get('total', 0))
            print(f"✅ OS corretivas: {total_corretiva}")
        else:
            print(f"❌ Erro com filtro tipo: {response.status_code}")
        
        # 5. Teste combinado: data + status + tipo
        print(f"\n🎯 === TESTE FILTRO COMBINADO ===")
        
        payload_combinado = payload_base.copy()
        payload_combinado.update({
            'data_abertura': '2025-11-01 - 2025-11-24',
            'status': 'A',
            'tipo': 'C'
        })
        
        response = requests.post(client.base_url, data=payload_combinado, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            total_combinado = int(data.get('total', 0))
            registros = data.get('registros', [])
            
            print(f"✅ OS com filtros combinados: {total_combinado}")
            print(f"   (Data: nov/2025, Status: Aberta, Tipo: Corretiva)")
            
            if total_combinado >= 56:
                print(f"🎉 ENCONTRAMOS AS 56+ OS! Total: {total_combinado}")
            elif total_combinado > 24:
                print(f"✅ Mais OS encontradas que no banco ({total_combinado} vs 24)")
            
            # Mostrar algumas
            print(f"📋 Exemplos das OS encontradas:")
            for i, os in enumerate(registros[:5], 1):
                id_os = os.get('id')
                protocolo = os.get('protocolo', 'N/A')
                data_abertura = os.get('data_abertura', 'N/A')
                status = os.get('status', 'N/A')
                tipo = os.get('tipo', 'N/A')
                print(f"   {i}. ID {id_os} - {protocolo} - {data_abertura} - {status}/{tipo}")
        else:
            print(f"❌ Erro com filtros combinados: {response.status_code}")
        
        # 6. Teste com diferentes ranges de data
        print(f"\n📅 === TESTE RANGES DE DATA DIFERENTES ===")
        
        ranges_teste = [
            ('2025-11-22 - 2025-11-24', 'Últimos 3 dias'),
            ('2025-11-01 - 2025-11-30', 'Mês todo'),
            ('2025-11-18 - 2025-11-22', 'Período com OS conhecidas'),
        ]
        
        for range_data, descricao in ranges_teste:
            payload_range = payload_base.copy()
            payload_range['data_abertura'] = range_data
            payload_range['status'] = 'A'
            
            response = requests.post(client.base_url, data=payload_range, headers=headers, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                total_range = int(data.get('total', 0))
                print(f"   {descricao}: {total_range} OS")
            else:
                print(f"   {descricao}: Erro {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def sync_with_correct_filters():
    """Sincroniza usando os filtros corretos"""
    print(f"\n🚀 === SINCRONIZAÇÃO COM FILTROS CORRETOS ===")
    
    try:
        from olt.client_utils import IxcOSClient
        from olt.models import OrdemServicoIxc
        
        client = IxcOSClient()
        
        # Usar filtros corretos para o período
        filtros_corretos = {
            'data_inicio': '2025-11-01',
            'data_fim': '2025-11-24',
            'status': 'A',  # Apenas abertas primeiro
            'tipo': 'C'     # Corretivas
        }
        
        print(f"Usando filtros: {filtros_corretos}")
        
        # Contar OS antes
        total_antes = OrdemServicoIxc.objects.count()
        print(f"OS no banco antes: {total_antes}")
        
        # Executar sincronização com limite
        sucesso = client.sincronizar_ordens_servico(limite_paginas=10)
        
        if sucesso:
            total_depois = OrdemServicoIxc.objects.count()
            novas = total_depois - total_antes
            
            print(f"✅ Sincronização concluída!")
            print(f"OS no banco depois: {total_depois}")
            print(f"Novas OS: {novas}")
            
            # Verificar período
            periodo_count = OrdemServicoIxc.objects.filter(
                data_abertura__date__gte='2025-11-01',
                data_abertura__date__lte='2025-11-24'
            ).count()
            
            print(f"OS do período nov: {periodo_count}")
            
            if periodo_count >= 56:
                print(f"🎉 META ATINGIDA! {periodo_count} OS")
            else:
                print(f"⚠️ Ainda faltam {56 - periodo_count} OS")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na sincronização: {e}")
        return False

if __name__ == '__main__':
    print("🚀 TESTE DE FILTROS CORRETOS")
    
    sucesso_teste = test_correct_filters()
    
    if sucesso_teste:
        print("\n" + "="*50)
        confirma = input("Executar sincronização com filtros corretos? (s/N): ").strip().lower()
        
        if confirma == 's':
            sync_with_correct_filters()
        
        print("\n🎉 PROCESSO CONCLUÍDO!")
    else:
        print("\n❌ TESTE FALHOU")
        sys.exit(1)