#!/usr/bin/env python
"""
Sincronização final com filtros corretos
Agora que descobrimos o Content-Type correto!
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def sync_final_with_correct_filters():
    """Sincronização final usando os filtros corretos"""
    print("=== SINCRONIZAÇÃO FINAL COM FILTROS CORRETOS ===")
    
    try:
        from olt.client_utils import IxcOSClient
        from olt.models import OrdemServicoIxc
        from datetime import date
        
        client = IxcOSClient()
        
        # Status inicial
        total_inicial = OrdemServicoIxc.objects.count()
        periodo_inicial = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte='2025-11-01',
            data_abertura__date__lte='2025-11-24'
        ).count()
        
        print(f"📊 STATUS INICIAL:")
        print(f"   Total OS no banco: {total_inicial}")
        print(f"   OS do período nov/2025: {periodo_inicial}")
        print(f"   Meta: 56 OS do período")
        print(f"   Faltam: {56 - periodo_inicial} OS")
        
        # 1. TESTAR FILTROS COM CONTENT-TYPE CORRETO
        print(f"\n🔍 === TESTANDO FILTROS CORRETOS ===")
        
        # Filtro por data do período
        filtros_data = {
            'data_inicio': '2025-11-01'
        }
        
        resultado_data = client.listar_ordens_servico(page=1, rp=100, filtros=filtros_data)
        
        if resultado_data:
            total_periodo_api = int(resultado_data.get('total', 0))
            registros_periodo = resultado_data.get('registros', [])
            
            print(f"✅ OS do período na API: {total_periodo_api}")
            print(f"✅ Registros retornados: {len(registros_periodo)}")
            
            if total_periodo_api >= 50:
                print(f"🎉 ENCONTRAMOS AS OS DO PERÍODO!")
                
                # Verificar quais estão faltando no banco
                os_faltando = []
                os_no_periodo = []
                
                for os_data in registros_periodo:
                    id_ixc = int(os_data.get('id', 0))
                    data_abertura = os_data.get('data_abertura', '')
                    
                    # Verificar se é realmente do período
                    if '2025-11-' in data_abertura:
                        os_no_periodo.append({
                            'id': id_ixc,
                            'protocolo': os_data.get('protocolo'),
                            'data_abertura': data_abertura,
                            'status': os_data.get('status'),
                            'tipo': os_data.get('tipo')
                        })
                        
                        # Verificar se não está no banco
                        if not OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists():
                            os_faltando.append({
                                'id': id_ixc,
                                'protocolo': os_data.get('protocolo'),
                                'data_abertura': data_abertura
                            })
                
                print(f"📋 OS do período encontradas: {len(os_no_periodo)}")
                print(f"📋 OS faltando no banco: {len(os_faltando)}")
                
                if len(os_no_periodo) >= 56:
                    print(f"🎉 TEMOS AS 56+ OS! Total: {len(os_no_periodo)}")
                
                # Mostrar algumas OS do período
                print(f"\n📋 Primeiras 10 OS do período:")
                for i, os in enumerate(os_no_periodo[:10], 1):
                    existe = "✅ No banco" if not any(f['id'] == os['id'] for f in os_faltando) else "❌ Faltando"
                    print(f"   {i}. ID {os['id']} - {os['protocolo']} - {os['data_abertura']} - {existe}")
                
                # 2. SINCRONIZAR OS FALTANTES
                if os_faltando:
                    print(f"\n🚀 === SINCRONIZANDO {len(os_faltando)} OS FALTANTES ===")
                    
                    sincronizadas = 0
                    for i, os_info in enumerate(os_faltando[:50], 1):  # Máximo 50 por vez
                        try:
                            print(f"   Sincronizando {i}/{len(os_faltando[:50])}: ID {os_info['id']}")
                            
                            # Usar método buscar_os_por_id
                            resultado_sync = client.buscar_os_por_id(os_info['id'])
                            
                            if resultado_sync:
                                sincronizadas += 1
                                print(f"      ✅ Sucesso: {os_info['protocolo']}")
                            else:
                                print(f"      ❌ Falha: {os_info['protocolo']}")
                                
                        except Exception as e:
                            print(f"      ❌ Erro: {e}")
                    
                    print(f"\n📊 Sincronizadas: {sincronizadas}/{len(os_faltando[:50])}")
                
                else:
                    print(f"✅ Todas as OS do período já estão sincronizadas!")
                
                # 3. BUSCAR MAIS PÁGINAS SE NECESSÁRIO
                if total_periodo_api > 100:
                    print(f"\n📄 === BUSCANDO MAIS PÁGINAS ({total_periodo_api} total) ===")
                    
                    paginas_adicionais = min(3, (total_periodo_api // 100))  # Máximo 3 páginas extras
                    
                    for pagina in range(2, paginas_adicionais + 2):
                        print(f"   Processando página {pagina}...")
                        
                        resultado_pag = client.listar_ordens_servico(page=pagina, rp=100, filtros=filtros_data)
                        
                        if resultado_pag and resultado_pag.get('registros'):
                            registros_pag = resultado_pag.get('registros', [])
                            
                            for os_data in registros_pag:
                                id_ixc = int(os_data.get('id', 0))
                                data_abertura = os_data.get('data_abertura', '')
                                
                                # Só processar se é do período e não existe no banco
                                if '2025-11-' in data_abertura and not OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists():
                                    try:
                                        client.buscar_os_por_id(id_ixc)
                                        print(f"      ✅ Página {pagina}: ID {id_ixc}")
                                    except:
                                        pass
            else:
                print(f"⚠️ Poucos registros encontrados: {total_periodo_api}")
        
        # 4. STATUS FINAL
        print(f"\n📊 === STATUS FINAL ===")
        
        total_final = OrdemServicoIxc.objects.count()
        periodo_final = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte='2025-11-01',
            data_abertura__date__lte='2025-11-24'
        ).count()
        
        incremento_total = total_final - total_inicial
        incremento_periodo = periodo_final - periodo_inicial
        
        print(f"Total OS no banco: {total_final} (+{incremento_total})")
        print(f"OS do período nov/2025: {periodo_final} (+{incremento_periodo})")
        
        if periodo_final >= 56:
            print(f"🎉 META ATINGIDA! {periodo_final} OS do período")
        else:
            print(f"⚠️ Ainda faltam {56 - periodo_final} OS para atingir a meta")
        
        # Estatísticas por status
        print(f"\n📈 Distribuição por status (período nov/2025):")
        status_counts = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte='2025-11-01',
            data_abertura__date__lte='2025-11-24'
        ).values('status').distinct()
        
        for status_info in status_counts:
            status = status_info['status']
            count = OrdemServicoIxc.objects.filter(
                data_abertura__date__gte='2025-11-01',
                data_abertura__date__lte='2025-11-24',
                status=status
            ).count()
            print(f"   {status}: {count} OS")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🎯 SINCRONIZAÇÃO FINAL - BUSCAR AS 56 OS!")
    print("Usando filtros corretos com Content-Type: application/x-www-form-urlencoded")
    
    sucesso = sync_final_with_correct_filters()
    
    if sucesso:
        print("\n🎉 PROCESSO CONCLUÍDO COM SUCESSO!")
    else:
        print("\n❌ PROCESSO FALHOU!")
        sys.exit(1)