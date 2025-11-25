#!/usr/bin/env python
"""
Script para investigar sincronização incompleta de OS
Verifica por que apenas 12 OS foram trazidas quando há 56 disponíveis
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def investigate_missing_os():
    """Investiga por que há OS faltando na sincronização"""
    print("=== INVESTIGAÇÃO DE OS FALTANTES NA SINCRONIZAÇÃO ===")
    
    try:
        from olt.client_utils import IxcOSClient
        from olt.models import OrdemServicoIxc
        from datetime import datetime, date
        
        client = IxcOSClient()
        
        # 1. Verificar quantas OS temos no banco
        print("\n📊 === STATUS ATUAL NO BANCO ===")
        
        total_banco = OrdemServicoIxc.objects.count()
        print(f"Total de OS no banco: {total_banco}")
        
        # OS abertas hoje
        hoje = date.today()
        os_hoje = OrdemServicoIxc.objects.filter(data_abertura__date=hoje).count()
        print(f"OS abertas hoje: {os_hoje}")
        
        # OS do período (1º novembro até hoje)
        from datetime import date
        inicio_mes = date(2025, 11, 1)
        os_periodo = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte=inicio_mes
        ).count()
        print(f"OS do período (01/11 até hoje): {os_periodo}")
        
        # 2. Testar consulta direta na API
        print(f"\n🔍 === TESTANDO CONSULTA DIRETA NA API ===")
        
        # Primeira página para ver total
        print("Consultando primeira página...")
        response = client.listar_ordens_servico(page=1, rp=100)
        
        if response:
            total_api = int(response.get('total', 0))
            registros_primeira_pagina = len(response.get('registros', []))
            
            print(f"✅ Total na API: {total_api} OS")
            print(f"✅ Registros primeira página: {registros_primeira_pagina}")
            
            # Verificar se há muito mais OS do que temos no banco
            diferenca = total_api - total_banco
            if diferenca > 0:
                print(f"⚠️ DIFERENÇA: {diferenca} OS não sincronizadas!")
            
            # Calcular quantas páginas seria necessário para todas
            paginas_necessarias = (total_api // 100) + (1 if total_api % 100 > 0 else 0)
            print(f"📄 Páginas necessárias para todas as OS: {paginas_necessarias}")
            
        else:
            print("❌ Erro ao consultar API")
            return False
        
        # 3. Verificar últimas OS na API vs Banco
        print(f"\n📋 === COMPARAÇÃO: ÚLTIMAS OS NA API vs BANCO ===")
        
        if response and response.get('registros'):
            print("🔹 Últimas 5 OS na API:")
            for i, os_api in enumerate(response['registros'][:5], 1):
                id_ixc = os_api.get('id')
                protocolo = os_api.get('protocolo', 'N/A')
                data_abertura = os_api.get('data_abertura', 'N/A')
                status = os_api.get('status', 'N/A')
                
                # Verificar se existe no banco
                existe_banco = OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists()
                status_banco = "✅ No banco" if existe_banco else "❌ Faltando"
                
                print(f"   {i}. ID {id_ixc} | {protocolo} | {data_abertura} | {status} | {status_banco}")
        
        print(f"\n🔹 Últimas 5 OS no banco:")
        ultimas_banco = OrdemServicoIxc.objects.order_by('-id_ixc')[:5]
        for i, os_banco in enumerate(ultimas_banco, 1):
            print(f"   {i}. ID {os_banco.id_ixc} | {os_banco.protocolo} | {os_banco.data_abertura} | {os_banco.status}")
        
        # 4. Testar busca com mais páginas
        print(f"\n📄 === TESTANDO MÚLTIPLAS PÁGINAS ===")
        
        paginas_teste = min(5, paginas_necessarias)  # Testar até 5 páginas
        print(f"Testando {paginas_teste} páginas...")
        
        total_encontradas = 0
        total_novas = 0
        
        for pagina in range(1, paginas_teste + 1):
            print(f"  Página {pagina}...")
            response_pagina = client.listar_ordens_servico(page=pagina, rp=100)
            
            if response_pagina and response_pagina.get('registros'):
                registros = response_pagina['registros']
                total_encontradas += len(registros)
                
                # Contar quantas são novas (não estão no banco)
                for registro in registros:
                    id_ixc = registro.get('id')
                    if id_ixc and not OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists():
                        total_novas += 1
                
                print(f"    Encontrados: {len(registros)} registros")
            else:
                print(f"    ❌ Erro ou página vazia")
                break
        
        print(f"📊 Total encontrado nas {paginas_teste} páginas: {total_encontradas}")
        print(f"📊 OS novas (não no banco): {total_novas}")
        
        # 5. Verificar filtros de data
        print(f"\n📅 === TESTANDO FILTROS DE DATA ===")
        
        # Testar com filtro de data do mês atual
        filtros_data = {
            'data_inicio': '2025-11-01',
            'data_fim': '2025-11-19'
        }
        
        print("Testando filtro de data (01/11/2025 - 19/11/2025)...")
        response_filtrada = client.listar_ordens_servico(page=1, rp=100, filtros=filtros_data)
        
        if response_filtrada:
            total_filtrada = int(response_filtrada.get('total', 0))
            registros_filtrada = len(response_filtrada.get('registros', []))
            
            print(f"✅ Total com filtro de data: {total_filtrada} OS")
            print(f"✅ Registros primeira página filtrada: {registros_filtrada}")
            
            if total_filtrada >= 56:
                print(f"🎯 ENCONTRADO! A API tem {total_filtrada} OS no período (≥ 56)")
                
                # Mostrar algumas das OS filtradas
                print("📋 Primeiras OS do período:")
                for i, os_periodo in enumerate(response_filtrada['registros'][:5], 1):
                    id_ixc = os_periodo.get('id')
                    protocolo = os_periodo.get('protocolo', 'N/A')
                    data_abertura = os_periodo.get('data_abertura', 'N/A')
                    
                    existe_banco = OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists()
                    status_banco = "✅" if existe_banco else "❌"
                    
                    print(f"   {i}. ID {id_ixc} | {protocolo} | {data_abertura} | {status_banco}")
            
        else:
            print("❌ Erro ao aplicar filtro de data")
        
        # 6. Análise do problema
        print(f"\n🔍 === ANÁLISE DO PROBLEMA ===")
        
        if total_api > total_banco:
            print(f"✅ PROBLEMA IDENTIFICADO:")
            print(f"   - API tem {total_api} OS total")
            print(f"   - Banco tem apenas {total_banco} OS")
            print(f"   - Faltando: {total_api - total_banco} OS")
            
            print(f"\n💡 POSSÍVEIS CAUSAS:")
            print(f"   1. Sincronização limitada por número de páginas")
            print(f"   2. Sincronização interrompida antes de completar")
            print(f"   3. Filtros aplicados durante sincronização")
            print(f"   4. Timeout na sincronização")
            
            print(f"\n🔧 SOLUÇÕES SUGERIDAS:")
            print(f"   1. Executar sincronização completa sem limite de páginas")
            print(f"   2. Aumentar timeout da sincronização")
            print(f"   3. Sincronizar em lotes menores")
            print(f"   4. Implementar sincronização incremental")
        
        # 7. Teste de sincronização de uma página adicional
        print(f"\n🚀 === TESTE DE SINCRONIZAÇÃO ADICIONAL ===")
        
        print("Tentando sincronizar página 2 para verificar se traz mais OS...")
        
        try:
            response_p2 = client.listar_ordens_servico(page=2, rp=100)
            
            if response_p2 and response_p2.get('registros'):
                registros_p2 = response_p2['registros']
                print(f"✅ Página 2 tem {len(registros_p2)} registros")
                
                # Verificar quantos são novos
                novos_p2 = 0
                for registro in registros_p2:
                    id_ixc = registro.get('id')
                    if id_ixc and not OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists():
                        novos_p2 += 1
                
                print(f"🎯 Registros novos na página 2: {novos_p2}")
                
                if novos_p2 > 0:
                    print("✅ CONFIRMADO: Há mais OS disponíveis para sincronização!")
                    
                    # Mostrar alguns exemplos
                    print("📋 Exemplos de OS não sincronizadas:")
                    count = 0
                    for registro in registros_p2:
                        id_ixc = registro.get('id')
                        if id_ixc and not OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists():
                            protocolo = registro.get('protocolo', 'N/A')
                            data_abertura = registro.get('data_abertura', 'N/A')
                            print(f"   - ID {id_ixc} | {protocolo} | {data_abertura}")
                            count += 1
                            if count >= 3:
                                break
                
            else:
                print("❌ Página 2 vazia ou erro")
                
        except Exception as e:
            print(f"❌ Erro ao testar página 2: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO NA INVESTIGAÇÃO: {e}")
        import traceback
        traceback.print_exc()
        return False

def suggest_sync_fix():
    """Sugere correções para o problema de sincronização"""
    print(f"\n🛠️ === SUGESTÕES DE CORREÇÃO ===")
    
    print("1. SINCRONIZAÇÃO COMPLETA:")
    print("   - Executar sincronização sem limite de páginas")
    print("   - Processar todas as páginas disponíveis")
    
    print("\n2. SINCRONIZAÇÃO INCREMENTAL:")
    print("   - Buscar apenas OS mais recentes que não estão no banco")
    print("   - Usar filtro de data da última sincronização")
    
    print("\n3. CONFIGURAÇÕES RECOMENDADAS:")
    print("   - Aumentar timeout para 30-60 segundos")
    print("   - Processar em lotes de 50-100 registros")
    print("   - Implementar retry em caso de falha")
    
    print("\n4. MONITORAMENTO:")
    print("   - Log detalhado do progresso")
    print("   - Verificação de integridade após sincronização")
    print("   - Alerta quando diferença > 10% entre API e banco")

if __name__ == '__main__':
    print("🚀 INICIANDO INVESTIGAÇÃO DE OS FALTANTES")
    
    sucesso = investigate_missing_os()
    
    if sucesso:
        suggest_sync_fix()
        print("\n🎉 INVESTIGAÇÃO CONCLUÍDA!")
    else:
        print("\n❌ INVESTIGAÇÃO FALHOU")
        sys.exit(1)