#!/usr/bin/env python
"""
Script para sincronizar apenas OS do período específico (01/nov - hoje)
usando filtros de data na API
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def sync_period_os():
    """Sincroniza OS de um período específico usando filtros"""
    print("=== SINCRONIZAÇÃO DE OS POR PERÍODO ===")
    
    try:
        from olt.client_utils import IxcOSClient
        from olt.models import OrdemServicoIxc
        from datetime import date, datetime
        from django.db import transaction
        
        # 1. Status inicial
        print(f"\n📊 === STATUS INICIAL ===")
        total_inicial = OrdemServicoIxc.objects.count()
        print(f"OS no banco: {total_inicial}")
        
        # OS do período no banco
        inicio_periodo = date(2025, 11, 1)
        fim_periodo = date.today()
        
        os_periodo_banco = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte=inicio_periodo,
            data_abertura__date__lte=fim_periodo
        ).count()
        
        print(f"OS do período (01/11 - hoje) no banco: {os_periodo_banco}")
        
        # 2. Testar filtro na API
        print(f"\n🔍 === TESTANDO FILTRO DE DATA NA API ===")
        
        client = IxcOSClient()
        
        # Formato de data para API
        data_inicio_api = inicio_periodo.strftime('%Y-%m-%d')
        data_fim_api = fim_periodo.strftime('%Y-%m-%d')
        
        print(f"Buscando OS entre {data_inicio_api} e {data_fim_api}")
        
        filtros = {
            'data_inicio': data_inicio_api,
            'data_fim': data_fim_api
        }
        
        # Buscar primeira página com filtro
        response = client.listar_ordens_servico(page=1, rp=100, filtros=filtros)
        
        if not response:
            print("❌ Erro ao consultar API com filtros")
            return False
        
        total_api_periodo = int(response.get('total', 0))
        print(f"✅ Total na API (período): {total_api_periodo} OS")
        
        if total_api_periodo == 0:
            print("⚠️ Nenhuma OS encontrada no período")
            return True
        
        # 3. Verificar se precisa buscar mais páginas
        paginas_necessarias = (total_api_periodo // 100) + (1 if total_api_periodo % 100 > 0 else 0)
        print(f"📄 Páginas necessárias: {paginas_necessarias}")
        
        # 4. Sincronizar todas as OS do período
        print(f"\n🚀 === SINCRONIZANDO OS DO PERÍODO ===")
        
        registros_processados = 0
        registros_criados = 0
        registros_atualizados = 0
        
        for pagina in range(1, paginas_necessarias + 1):
            print(f"Processando página {pagina}/{paginas_necessarias}...")
            
            response_pagina = client.listar_ordens_servico(
                page=pagina, 
                rp=100, 
                filtros=filtros
            )
            
            if not response_pagina or not response_pagina.get('registros'):
                print(f"  ❌ Página {pagina} vazia ou erro")
                continue
            
            registros = response_pagina['registros']
            print(f"  ✅ {len(registros)} registros na página {pagina}")
            
            # Processar cada registro
            with transaction.atomic():
                for registro in registros:
                    try:
                        id_ixc = int(registro.get('id', 0))
                        if not id_ixc:
                            continue
                        
                        # Verificar se já existe
                        if OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists():
                            registros_atualizados += 1
                            continue
                        
                        # Converter datas
                        data_abertura = client._converter_data(registro.get('data_abertura'))
                        data_agenda = client._converter_data(registro.get('data_agenda'))
                        data_execucao = client._converter_data(registro.get('data_hora_execucao'))
                        data_fechamento = client._converter_data(registro.get('data_fechamento'))
                        data_prazo_limite = client._converter_data(registro.get('data_prazo_limite'))
                        
                        # Converter valores financeiros
                        valor_total = client._converter_valor(registro.get('valor_total'))
                        valor_comissao = client._converter_valor(registro.get('valor_total_comissao'))
                        
                        # Buscar assunto
                        id_assunto = client._converter_int(registro.get('id_assunto'))
                        assunto_nome = registro.get('assunto_nome')
                        
                        if id_assunto and not assunto_nome:
                            assunto_nome = client.get_subject_name(id_assunto)
                        
                        # Dados da OS
                        dados_os = {
                            'protocolo': registro.get('protocolo'),
                            'tipo': registro.get('tipo', 'M'),
                            'status': registro.get('status', 'A'),
                            'prioridade': registro.get('prioridade', 'N'),
                            'id_cliente': client._converter_int(registro.get('id_cliente')),
                            'id_contrato': client._converter_int(registro.get('id_contrato_kit')),
                            'id_assunto': id_assunto,
                            'assunto_nome': assunto_nome,
                            'mensagem': registro.get('mensagem'),
                            'mensagem_resposta': registro.get('mensagem_resposta'),
                            'id_tecnico': client._converter_int(registro.get('id_tecnico')),
                            'tecnico_nome': registro.get('tecnico_nome'),
                            'endereco': registro.get('endereco'),
                            'bairro': registro.get('bairro'),
                            'cidade': registro.get('cidade'),
                            'referencia': registro.get('referencia'),
                            'data_abertura': data_abertura,
                            'data_agenda': data_agenda,
                            'data_execucao': data_execucao,
                            'data_fechamento': data_fechamento,
                            'data_prazo_limite': data_prazo_limite,
                            'valor_total': valor_total,
                            'valor_comissao': valor_comissao,
                        }
                        
                        # Criar registro
                        OrdemServicoIxc.objects.create(id_ixc=id_ixc, **dados_os)
                        registros_criados += 1
                        print(f"    ✅ Nova OS {id_ixc} - {registro.get('protocolo')}")
                        
                        registros_processados += 1
                        
                    except Exception as e:
                        print(f"    ❌ Erro no registro {registro.get('id', 'N/A')}: {e}")
                        continue
        
        # 5. Resultado final
        print(f"\n📊 === RESULTADO DA SINCRONIZAÇÃO ===")
        print(f"✅ Registros processados: {registros_processados}")
        print(f"🆕 Registros criados: {registros_criados}")
        print(f"🔄 Registros já existentes: {registros_atualizados}")
        
        # Status final
        total_final = OrdemServicoIxc.objects.count()
        os_periodo_final = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte=inicio_periodo,
            data_abertura__date__lte=fim_periodo
        ).count()
        
        print(f"\n📈 === STATUS FINAL ===")
        print(f"OS no banco total: {total_inicial} → {total_final} (+{total_final - total_inicial})")
        print(f"OS do período: {os_periodo_banco} → {os_periodo_final} (+{os_periodo_final - os_periodo_banco})")
        
        if os_periodo_final >= 56:
            print(f"🎉 META ATINGIDA! Temos {os_periodo_final} OS do período (meta: 56)")
        else:
            faltando = 56 - os_periodo_final
            print(f"⚠️ Ainda faltam {faltando} OS para atingir a meta de 56")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_period_details():
    """Analisa detalhes das OS do período"""
    print(f"\n📊 === ANÁLISE DETALHADA DO PERÍODO ===")
    
    try:
        from olt.models import OrdemServicoIxc
        from datetime import date
        from django.db.models import Count
        
        inicio_periodo = date(2025, 11, 1)
        fim_periodo = date.today()
        
        os_periodo = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte=inicio_periodo,
            data_abertura__date__lte=fim_periodo
        )
        
        print(f"📅 Período: {inicio_periodo} até {fim_periodo}")
        print(f"📊 Total de OS no período: {os_periodo.count()}")
        
        # Por data
        print(f"\n📅 OS por data:")
        os_por_data = os_periodo.values('data_abertura__date').annotate(
            count=Count('id')
        ).order_by('-data_abertura__date')[:10]
        
        for item in os_por_data:
            data_str = item['data_abertura__date'].strftime('%d/%m/%Y')
            count = item['count']
            print(f"   {data_str}: {count} OS")
        
        # Por assunto
        print(f"\n🎯 OS por assunto:")
        os_por_assunto = os_periodo.values('assunto_nome').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        for item in os_por_assunto:
            assunto = item['assunto_nome'] or '(Sem assunto)'
            count = item['count']
            print(f"   {assunto}: {count} OS")
        
        # Por status
        print(f"\n📋 OS por status:")
        os_por_status = os_periodo.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        status_map = {'A': 'Aberta', 'F': 'Fechada', 'C': 'Cancelada'}
        
        for item in os_por_status:
            status_key = item['status']
            status_nome = status_map.get(status_key, status_key)
            count = item['count']
            print(f"   {status_nome}: {count} OS")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        return False

if __name__ == '__main__':
    print("🚀 SINCRONIZAÇÃO DE OS POR PERÍODO")
    
    sucesso = sync_period_os()
    
    if sucesso:
        analyze_period_details()
        print("\n🎉 SINCRONIZAÇÃO POR PERÍODO CONCLUÍDA!")
    else:
        print("\n❌ SINCRONIZAÇÃO FALHOU")
        sys.exit(1)