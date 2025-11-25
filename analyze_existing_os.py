#!/usr/bin/env python
"""
Script para analisar as OS existentes e ver se realmente temos todas as do período
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def analyze_existing_os():
    """Analisa as OS existentes para entender o padrão"""
    print("=== ANÁLISE DAS OS EXISTENTES ===")
    
    try:
        from olt.models import OrdemServicoIxc
        from datetime import date, timedelta
        from django.db.models import Count, Q
        
        # 1. OS por dia
        print(f"\n📅 === OS POR DIA ===")
        
        inicio = date(2025, 11, 1)
        fim = date.today()
        
        print(f"Período analisado: {inicio} até {fim}")
        
        current_date = inicio
        total_periodo = 0
        dias_com_os = 0
        
        while current_date <= fim:
            os_dia = OrdemServicoIxc.objects.filter(
                data_abertura__date=current_date
            ).count()
            
            if os_dia > 0:
                print(f"   {current_date.strftime('%d/%m/%Y')}: {os_dia} OS")
                total_periodo += os_dia
                dias_com_os += 1
            
            current_date += timedelta(days=1)
        
        print(f"\n📊 Resumo:")
        print(f"   Total de OS no período: {total_periodo}")
        print(f"   Dias com OS: {dias_com_os}")
        print(f"   Dias sem OS: {(fim - inicio).days + 1 - dias_com_os}")
        
        # 2. Verificar lacunas nos IDs
        print(f"\n🔍 === ANÁLISE DE IDS ===")
        
        os_ordenadas = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte=inicio,
            data_abertura__date__lte=fim
        ).order_by('id_ixc')
        
        if os_ordenadas.exists():
            primeiro_id = os_ordenadas.first().id_ixc
            ultimo_id = os_ordenadas.last().id_ixc
            total_ids = ultimo_id - primeiro_id + 1
            
            print(f"   Primeiro ID: {primeiro_id}")
            print(f"   Último ID: {ultimo_id}")
            print(f"   Range de IDs: {total_ids}")
            print(f"   OS no banco: {os_ordenadas.count()}")
            print(f"   IDs faltando: {total_ids - os_ordenadas.count()}")
            
            if total_ids - os_ordenadas.count() > 0:
                print(f"\n🔍 IDs potencialmente faltando:")
                
                ids_existentes = set(os_ordenadas.values_list('id_ixc', flat=True))
                ids_faltando = []
                
                for id_check in range(primeiro_id, ultimo_id + 1):
                    if id_check not in ids_existentes:
                        ids_faltando.append(id_check)
                
                if ids_faltando:
                    print(f"   Primeiros 10 IDs faltando: {ids_faltando[:10]}")
                    if len(ids_faltando) > 10:
                        print(f"   ... e mais {len(ids_faltando) - 10} IDs")
        
        # 3. Verificar padrão de protocolos
        print(f"\n📋 === ANÁLISE DE PROTOCOLOS ===")
        
        protocolos = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte=inicio,
            data_abertura__date__lte=fim
        ).order_by('-id_ixc').values_list('protocolo', 'id_ixc', 'data_abertura')[:10]
        
        print(f"   Últimos 10 protocolos:")
        for protocolo, id_ixc, data in protocolos:
            data_str = data.strftime('%d/%m/%Y %H:%M') if data else 'N/A'
            print(f"   {protocolo} (ID {id_ixc}) - {data_str}")
        
        # 4. Verificar se há OS muito recentes que não estão no banco
        print(f"\n🕒 === VERIFICAR OS MAIS RECENTES ===")
        
        from olt.client_utils import IxcOSClient
        
        client = IxcOSClient()
        
        # Buscar as 20 OS mais recentes da API
        response = client.listar_ordens_servico(page=1, rp=20)
        
        if response and response.get('registros'):
            print(f"   Últimas 20 OS da API:")
            
            os_na_api_nao_no_banco = []
            
            for os_api in response['registros']:
                id_ixc = int(os_api.get('id', 0))
                protocolo = os_api.get('protocolo', 'N/A')
                data_abertura = os_api.get('data_abertura', 'N/A')
                
                existe_banco = OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists()
                status = "✅" if existe_banco else "❌"
                
                print(f"   {protocolo} (ID {id_ixc}) - {data_abertura} {status}")
                
                if not existe_banco:
                    os_na_api_nao_no_banco.append({
                        'id': id_ixc,
                        'protocolo': protocolo,
                        'data': data_abertura
                    })
            
            if os_na_api_nao_no_banco:
                print(f"\n⚠️ {len(os_na_api_nao_no_banco)} OS na API que NÃO estão no banco:")
                for os_faltando in os_na_api_nao_no_banco:
                    print(f"   - ID {os_faltando['id']}: {os_faltando['protocolo']} ({os_faltando['data']})")
            else:
                print(f"\n✅ Todas as OS recentes da API estão no banco")
        
        # 5. Conclusão
        print(f"\n🎯 === CONCLUSÃO ===")
        
        if total_periodo >= 56:
            print(f"✅ META ATINGIDA! Temos {total_periodo} OS (meta: 56)")
            print(f"   O sistema já tem mais OS do que a meta de 56")
        elif total_periodo >= 30:
            print(f"⚠️ Próximo da meta: {total_periodo}/56 OS ({(total_periodo/56)*100:.1f}%)")
            print(f"   Faltam apenas {56 - total_periodo} OS")
        else:
            print(f"❌ Longe da meta: {total_periodo}/56 OS ({(total_periodo/56)*100:.1f}%)")
            print(f"   Faltam {56 - total_periodo} OS")
        
        print(f"\n💡 Possíveis razões para diferença:")
        print(f"   1. Filtros da API não funcionam corretamente")
        print(f"   2. Há OS em outros status não sincronizadas")  
        print(f"   3. Há OS canceladas/deletadas no IXC")
        print(f"   4. A meta de 56 inclui períodos diferentes")
        print(f"   5. Algumas OS foram criadas mas depois removidas")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 ANÁLISE DAS OS EXISTENTES")
    
    sucesso = analyze_existing_os()
    
    if sucesso:
        print("\n🎉 ANÁLISE CONCLUÍDA!")
    else:
        print("\n❌ ANÁLISE FALHOU")
        sys.exit(1)