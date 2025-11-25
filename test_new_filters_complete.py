#!/usr/bin/env python
"""
Teste da nova implementação de filtros baseada no exemplo oficial do IXC
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_new_filters():
    """Testa os novos filtros baseados no exemplo oficial do IXC"""
    print("=== TESTE DOS NOVOS FILTROS IXC ===")
    
    try:
        from olt.client_utils import IxcOSClient
        from olt.models import OrdemServicoIxc
        
        client = IxcOSClient()
        
        # Status inicial
        total_banco_inicial = OrdemServicoIxc.objects.count()
        print(f"📊 OS no banco: {total_banco_inicial}")
        
        # 1. TESTE SEM FILTROS (baseline)
        print(f"\n🔍 === TESTE SEM FILTROS ===")
        resultado_sem_filtro = client.listar_ordens_servico(page=1, rp=10)
        
        if resultado_sem_filtro:
            total_sem_filtro = int(resultado_sem_filtro.get('total', 0))
            print(f"✅ Total sem filtros: {total_sem_filtro} OS")
        else:
            print("❌ Erro ao buscar sem filtros")
            return False
        
        # 2. TESTE FILTRO POR ID ESPECÍFICO  
        print(f"\n🎯 === TESTE FILTRO ID ESPECÍFICO ===")
        
        # Testar com uma OS que sabemos que existe (das últimas)
        id_teste = 15350
        filtros_id = {'id_especifico': id_teste}
        resultado_id = client.listar_ordens_servico(page=1, rp=1, filtros=filtros_id)
        
        if resultado_id:
            total_id = int(resultado_id.get('total', 0))
            registros = resultado_id.get('registros', [])
            
            print(f"Busca por ID {id_teste}: {total_id} registros")
            
            if total_id == 1 and registros:
                os_encontrada = registros[0]
                print(f"✅ OS {id_teste} encontrada: {os_encontrada.get('protocolo')} - {os_encontrada.get('data_abertura')}")
            elif total_id == 0:
                print(f"⚠️ OS {id_teste} não encontrada na API")
            else:
                print(f"⚠️ Resultado inesperado: {total_id} registros")
        
        # 3. TESTE FILTRO POR RANGE DE IDs
        print(f"\n📊 === TESTE FILTRO RANGE DE IDs ===")
        
        ranges_teste = [
            ({'id_minimo': 15300}, "ID >= 15300"),
            ({'id_minimo': 15350}, "ID >= 15350"),
            ({'id_minimo': 15295}, "ID >= 15295"),
        ]
        
        resultados_ranges = {}
        
        for filtro, descricao in ranges_teste:
            resultado = client.listar_ordens_servico(page=1, rp=10, filtros=filtro)
            if resultado:
                total = int(resultado.get('total', 0))
                print(f"   {descricao}: {total} OS")
                resultados_ranges[descricao] = total
                
                if total != total_sem_filtro and total > 0:
                    print(f"   ✅ FILTRO FUNCIONOU! ({total_sem_filtro} -> {total})")
        
        # 4. TESTE FILTRO POR DATA
        print(f"\n📅 === TESTE FILTRO POR DATA ===")
        
        filtros_data = [
            ({'data_inicio': '2025-11-01'}, "Data >= 2025-11-01"),
            ({'data_inicio': '2025-11-20'}, "Data >= 2025-11-20"), 
            ({'data_inicio': '2025-11-01', 'data_fim': '2025-11-24'}, "Data entre 01/11 e 24/11"),
        ]
        
        for filtro, descricao in filtros_data:
            resultado = client.listar_ordens_servico(page=1, rp=10, filtros=filtro)
            if resultado:
                total = int(resultado.get('total', 0))
                registros = resultado.get('registros', [])
                
                print(f"   {descricao}: {total} OS")
                
                if total != total_sem_filtro and total > 0:
                    print(f"   ✅ FILTRO DATA FUNCIONOU!")
                    
                    # Mostrar algumas OS encontradas
                    print(f"   📋 Primeiras OS encontradas:")
                    for i, os in enumerate(registros[:3], 1):
                        id_os = os.get('id')
                        protocolo = os.get('protocolo')
                        data_abertura = os.get('data_abertura')
                        print(f"      {i}. ID {id_os} - {protocolo} - {data_abertura}")
                    
                    if total >= 50:  # Se encontrou muitas OS do período
                        print(f"   🎉 ENCONTRADAS {total} OS DO PERÍODO!")
                        return test_specific_sync(client, filtro, total)
        
        # 5. TESTE FILTRO POR STATUS
        print(f"\n📋 === TESTE FILTRO POR STATUS ===")
        
        filtros_status = [
            ({'status': 'A'}, "Status = Aberta"),
            ({'status': 'X'}, "Status = Executada"),
            ({'status': 'F'}, "Status = Fechada"),
        ]
        
        for filtro, descricao in filtros_status:
            resultado = client.listar_ordens_servico(page=1, rp=10, filtros=filtro)
            if resultado:
                total = int(resultado.get('total', 0))
                print(f"   {descricao}: {total} OS")
                
                if total != total_sem_filtro and total > 0:
                    print(f"   ✅ FILTRO STATUS FUNCIONOU!")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_specific_sync(client, filtro_efetivo, total_encontrado):
    """Testa sincronização específica com filtro que funcionou"""
    print(f"\n🚀 === SINCRONIZAÇÃO COM FILTRO ESPECÍFICO ===")
    
    try:
        from olt.models import OrdemServicoIxc
        
        print(f"Filtro efetivo: {filtro_efetivo}")
        print(f"Total encontrado na API: {total_encontrado}")
        
        # Status antes
        total_antes = OrdemServicoIxc.objects.count()
        periodo_antes = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte='2025-11-01',
            data_abertura__date__lte='2025-11-24'
        ).count()
        
        print(f"Antes - Total banco: {total_antes}, Período nov: {periodo_antes}")
        
        # Buscar OS específicas do filtro
        resultado = client.listar_ordens_servico(page=1, rp=100, filtros=filtro_efetivo)
        
        if resultado and resultado.get('registros'):
            registros = resultado.get('registros', [])
            
            print(f"📋 Processando {len(registros)} OS encontradas...")
            
            # Verificar quais não estão no banco
            os_faltando = []
            for os_data in registros:
                id_ixc = int(os_data.get('id', 0))
                if not OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists():
                    os_faltando.append({
                        'id': id_ixc,
                        'protocolo': os_data.get('protocolo'),
                        'data_abertura': os_data.get('data_abertura')
                    })
            
            print(f"📊 OS faltando no banco: {len(os_faltando)}")
            
            if os_faltando:
                print(f"🔧 Sincronizando OS faltantes...")
                
                sincronizadas = 0
                for os_info in os_faltando[:20]:  # Máximo 20 por vez
                    try:
                        resultado_sync = client.buscar_os_por_id(os_info['id'])
                        if resultado_sync:
                            print(f"   ✅ Sincronizada: ID {os_info['id']} - {os_info['protocolo']}")
                            sincronizadas += 1
                        else:
                            print(f"   ❌ Erro ao sincronizar: ID {os_info['id']}")
                    except Exception as e:
                        print(f"   ❌ Erro ID {os_info['id']}: {e}")
                
                print(f"📊 Resultado da sincronização: {sincronizadas} OS")
                
                # Status depois
                total_depois = OrdemServicoIxc.objects.count()
                periodo_depois = OrdemServicoIxc.objects.filter(
                    data_abertura__date__gte='2025-11-01',
                    data_abertura__date__lte='2025-11-24'
                ).count()
                
                print(f"Depois - Total banco: {total_depois}, Período nov: {periodo_depois}")
                print(f"Incremento - Total: +{total_depois - total_antes}, Período: +{periodo_depois - periodo_antes}")
                
                if periodo_depois >= 56:
                    print(f"🎉 META ATINGIDA! {periodo_depois} OS do período novembro")
                else:
                    print(f"⚠️ Ainda faltam {56 - periodo_depois} OS para atingir a meta")
            
            else:
                print("✅ Todas as OS já estão sincronizadas")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na sincronização: {e}")
        return False

def check_final_status():
    """Verifica status final das OS"""
    print(f"\n📊 === STATUS FINAL ===")
    
    try:
        from olt.models import OrdemServicoIxc
        from datetime import date
        
        # Totais gerais
        total_geral = OrdemServicoIxc.objects.count()
        print(f"Total geral de OS: {total_geral}")
        
        # Por período
        periodo_nov = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte='2025-11-01',
            data_abertura__date__lte='2025-11-24'
        ).count()
        
        print(f"OS do período nov/2025: {periodo_nov}")
        
        # Por status no período
        por_status = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte='2025-11-01',
            data_abertura__date__lte='2025-11-24'
        ).values('status').distinct()
        
        print(f"Status das OS do período:")
        for status_info in por_status:
            status = status_info['status']
            count = OrdemServicoIxc.objects.filter(
                data_abertura__date__gte='2025-11-01',
                data_abertura__date__lte='2025-11-24',
                status=status
            ).count()
            print(f"   {status}: {count} OS")
        
        # Meta atingida?
        if periodo_nov >= 56:
            print(f"🎉 META ATINGIDA! {periodo_nov} OS (esperado: 56)")
        else:
            print(f"⚠️ Meta não atingida: {periodo_nov} OS (faltam: {56 - periodo_nov})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == '__main__':
    print("🧪 TESTE DOS NOVOS FILTROS BASEADOS NO EXEMPLO IXC")
    
    sucesso = test_new_filters()
    
    if sucesso:
        check_final_status()
        print("\n🎉 TESTE CONCLUÍDO!")
    else:
        print("\n❌ TESTE FALHOU!")
        sys.exit(1)