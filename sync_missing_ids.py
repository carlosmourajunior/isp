#!/usr/bin/env python
"""
Script para sincronizar IDs específicos faltando no range das OS
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def sync_missing_ids():
    """Sincroniza IDs específicos que estão faltando"""
    print("=== SINCRONIZAÇÃO DE IDS FALTANTES ===")
    
    try:
        from olt.models import OrdemServicoIxc
        from olt.client_utils import IxcOSClient
        from django.db import transaction
        
        # 1. Identificar IDs faltantes
        print(f"\n🔍 === IDENTIFICANDO IDS FALTANTES ===")
        
        os_existentes = OrdemServicoIxc.objects.order_by('id_ixc')
        
        if not os_existentes.exists():
            print("❌ Nenhuma OS no banco")
            return False
        
        primeiro_id = os_existentes.first().id_ixc
        ultimo_id = os_existentes.last().id_ixc
        
        print(f"Range de IDs: {primeiro_id} - {ultimo_id}")
        
        # Encontrar IDs faltantes
        ids_existentes = set(os_existentes.values_list('id_ixc', flat=True))
        ids_faltantes = []
        
        for id_check in range(primeiro_id, ultimo_id + 1):
            if id_check not in ids_existentes:
                ids_faltantes.append(id_check)
        
        print(f"IDs faltantes encontrados: {len(ids_faltantes)}")
        print(f"Primeiros 10: {ids_faltantes[:10]}")
        
        if not ids_faltantes:
            print("✅ Nenhum ID faltante no range")
            return True
        
        # 2. Tentar buscar IDs faltantes na API
        print(f"\n🚀 === SINCRONIZANDO IDS FALTANTES ===")
        
        client = IxcOSClient()
        
        ids_encontrados = 0
        ids_criados = 0
        ids_nao_existem = 0
        
        for id_faltante in ids_faltantes:
            print(f"Buscando ID {id_faltante}...")
            
            try:
                # Tentar buscar OS específica por ID
                os_data = client.obter_ordem_servico(id_faltante)
                
                if os_data:
                    print(f"  ✅ OS {id_faltante} encontrada na API")
                    ids_encontrados += 1
                    
                    try:
                        with transaction.atomic():
                            # Converter dados como na sincronização normal
                            data_abertura = client._converter_data(os_data.get('data_abertura'))
                            data_agenda = client._converter_data(os_data.get('data_agenda'))
                            data_execucao = client._converter_data(os_data.get('data_hora_execucao'))
                            data_fechamento = client._converter_data(os_data.get('data_fechamento'))
                            data_prazo_limite = client._converter_data(os_data.get('data_prazo_limite'))
                            
                            valor_total = client._converter_valor(os_data.get('valor_total'))
                            valor_comissao = client._converter_valor(os_data.get('valor_total_comissao'))
                            
                            # Buscar assunto
                            id_assunto = client._converter_int(os_data.get('id_assunto'))
                            assunto_nome = os_data.get('assunto_nome')
                            
                            if id_assunto and not assunto_nome:
                                assunto_nome = client.get_subject_name(id_assunto)
                            
                            # Criar OS
                            dados_os = {
                                'id_ixc': id_faltante,
                                'protocolo': os_data.get('protocolo'),
                                'tipo': os_data.get('tipo', 'M'),
                                'status': os_data.get('status', 'A'),
                                'prioridade': os_data.get('prioridade', 'N'),
                                'id_cliente': client._converter_int(os_data.get('id_cliente')),
                                'id_contrato': client._converter_int(os_data.get('id_contrato_kit')),
                                'id_assunto': id_assunto,
                                'assunto_nome': assunto_nome,
                                'mensagem': os_data.get('mensagem'),
                                'mensagem_resposta': os_data.get('mensagem_resposta'),
                                'id_tecnico': client._converter_int(os_data.get('id_tecnico')),
                                'tecnico_nome': os_data.get('tecnico_nome'),
                                'endereco': os_data.get('endereco'),
                                'bairro': os_data.get('bairro'),
                                'cidade': os_data.get('cidade'),
                                'referencia': os_data.get('referencia'),
                                'data_abertura': data_abertura,
                                'data_agenda': data_agenda,
                                'data_execucao': data_execucao,
                                'data_fechamento': data_fechamento,
                                'data_prazo_limite': data_prazo_limite,
                                'valor_total': valor_total,
                                'valor_comissao': valor_comissao,
                            }
                            
                            OrdemServicoIxc.objects.create(**dados_os)
                            ids_criados += 1
                            
                            protocolo = os_data.get('protocolo', 'N/A')
                            data_str = data_abertura.strftime('%d/%m/%Y') if data_abertura else 'N/A'
                            print(f"  🎉 Criada OS {id_faltante} - {protocolo} ({data_str})")
                            
                    except Exception as e:
                        print(f"  ❌ Erro ao criar OS {id_faltante}: {e}")
                        
                else:
                    print(f"  ⚠️ OS {id_faltante} não existe na API")
                    ids_nao_existem += 1
                    
            except Exception as e:
                print(f"  ❌ Erro ao buscar OS {id_faltante}: {e}")
                ids_nao_existem += 1
        
        # 3. Resultado
        print(f"\n📊 === RESULTADO ===")
        print(f"IDs verificados: {len(ids_faltantes)}")
        print(f"IDs encontrados na API: {ids_encontrados}")
        print(f"IDs criados no banco: {ids_criados}")
        print(f"IDs que não existem: {ids_nao_existem}")
        
        # 4. Status final
        total_final = OrdemServicoIxc.objects.count()
        periodo_final = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte='2025-11-01',
            data_abertura__date__lte='2025-11-24'
        ).count()
        
        print(f"\n📈 === STATUS FINAL ===")
        print(f"Total de OS no banco: {total_final}")
        print(f"OS do período nov: {periodo_final}")
        
        if periodo_final >= 56:
            print(f"🎉 META ATINGIDA! {periodo_final} OS (meta: 56)")
        else:
            faltam = 56 - periodo_final
            print(f"⚠️ Ainda faltam {faltam} OS para meta de 56")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_completion():
    """Verifica se a sincronização foi completa"""
    print(f"\n✅ === VERIFICAÇÃO FINAL ===")
    
    try:
        from olt.models import OrdemServicoIxc
        from django.db.models import Count
        from datetime import date
        
        # Status geral
        total = OrdemServicoIxc.objects.count()
        print(f"Total de OS: {total}")
        
        # Por período
        periodo = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte='2025-11-01',
            data_abertura__date__lte='2025-11-24'
        )
        
        total_periodo = periodo.count()
        print(f"OS do período: {total_periodo}")
        
        # Por data
        print(f"\nOS por data:")
        por_data = periodo.values('data_abertura__date').annotate(
            count=Count('id')
        ).order_by('data_abertura__date')
        
        for item in por_data:
            data_str = item['data_abertura__date'].strftime('%d/%m/%Y')
            count = item['count']
            print(f"   {data_str}: {count} OS")
        
        # Por assunto
        print(f"\nTop assuntos:")
        por_assunto = periodo.values('assunto_nome').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        for item in por_assunto:
            assunto = item['assunto_nome'] or '(Sem assunto)'
            count = item['count']
            print(f"   {assunto}: {count} OS")
        
        # Verificar lacunas
        os_ordenadas = periodo.order_by('id_ixc')
        if os_ordenadas.count() > 1:
            primeiro = os_ordenadas.first().id_ixc
            ultimo = os_ordenadas.last().id_ixc
            range_ids = ultimo - primeiro + 1
            
            print(f"\nRange de IDs: {primeiro} - {ultimo} ({range_ids} possíveis)")
            print(f"OS no banco: {os_ordenadas.count()}")
            
            lacunas = range_ids - os_ordenadas.count()
            if lacunas == 0:
                print(f"✅ Nenhuma lacuna nos IDs!")
            else:
                print(f"⚠️ {lacunas} IDs ainda faltando")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

if __name__ == '__main__':
    print("🚀 SINCRONIZAÇÃO DE IDS FALTANTES")
    
    sucesso = sync_missing_ids()
    
    if sucesso:
        verify_completion()
        print("\n🎉 PROCESSO CONCLUÍDO!")
    else:
        print("\n❌ PROCESSO FALHOU")
        sys.exit(1)