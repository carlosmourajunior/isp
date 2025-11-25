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
        
        for pagina in range(1, paginas_necessarias + 1):\n            print(f\"Processando página {pagina}/{paginas_necessarias}...\")\n            \n            response_pagina = client.listar_ordens_servico(\n                page=pagina, \n                rp=100, \n                filtros=filtros\n            )\n            \n            if not response_pagina or not response_pagina.get('registros'):\n                print(f\"  ❌ Página {pagina} vazia ou erro\")\n                continue\n            \n            registros = response_pagina['registros']\n            print(f\"  ✅ {len(registros)} registros na página {pagina}\")\n            \n            # Processar cada registro\n            with transaction.atomic():\n                for registro in registros:\n                    try:\n                        id_ixc = int(registro.get('id', 0))\n                        if not id_ixc:\n                            continue\n                        \n                        # Converter datas\n                        data_abertura = client._converter_data(registro.get('data_abertura'))\n                        data_agenda = client._converter_data(registro.get('data_agenda'))\n                        data_execucao = client._converter_data(registro.get('data_hora_execucao'))\n                        data_fechamento = client._converter_data(registro.get('data_fechamento'))\n                        data_prazo_limite = client._converter_data(registro.get('data_prazo_limite'))\n                        \n                        # Converter valores financeiros\n                        valor_total = client._converter_valor(registro.get('valor_total'))\n                        valor_comissao = client._converter_valor(registro.get('valor_total_comissao'))\n                        \n                        # Buscar assunto\n                        id_assunto = client._converter_int(registro.get('id_assunto'))\n                        assunto_nome = registro.get('assunto_nome')\n                        \n                        if id_assunto and not assunto_nome:\n                            assunto_nome = client.get_subject_name(id_assunto)\n                        \n                        # Dados da OS\n                        dados_os = {\n                            'protocolo': registro.get('protocolo'),\n                            'tipo': registro.get('tipo', 'M'),\n                            'status': registro.get('status', 'A'),\n                            'prioridade': registro.get('prioridade', 'N'),\n                            'id_cliente': client._converter_int(registro.get('id_cliente')),\n                            'id_contrato': client._converter_int(registro.get('id_contrato_kit')),\n                            'id_assunto': id_assunto,\n                            'assunto_nome': assunto_nome,\n                            'mensagem': registro.get('mensagem'),\n                            'mensagem_resposta': registro.get('mensagem_resposta'),\n                            'id_tecnico': client._converter_int(registro.get('id_tecnico')),\n                            'tecnico_nome': registro.get('tecnico_nome'),\n                            'endereco': registro.get('endereco'),\n                            'bairro': registro.get('bairro'),\n                            'cidade': registro.get('cidade'),\n                            'referencia': registro.get('referencia'),\n                            'data_abertura': data_abertura,\n                            'data_agenda': data_agenda,\n                            'data_execucao': data_execucao,\n                            'data_fechamento': data_fechamento,\n                            'data_prazo_limite': data_prazo_limite,\n                            'valor_total': valor_total,\n                            'valor_comissao': valor_comissao,\n                        }\n                        \n                        # Criar ou atualizar registro\n                        os_obj, created = OrdemServicoIxc.objects.update_or_create(\n                            id_ixc=id_ixc,\n                            defaults=dados_os\n                        )\n                        \n                        if created:\n                            registros_criados += 1\n                            print(f\"    ✅ Criada OS {id_ixc} - {registro.get('protocolo')}\")\n                        else:\n                            registros_atualizados += 1\n                        \n                        registros_processados += 1\n                        \n                    except Exception as e:\n                        print(f\"    ❌ Erro no registro {registro.get('id', 'N/A')}: {e}\")\n                        continue\n        \n        # 5. Resultado final\n        print(f\"\\n📊 === RESULTADO DA SINCRONIZAÇÃO ===\\n\")\n        print(f\"✅ Registros processados: {registros_processados}\")\n        print(f\"🆕 Registros criados: {registros_criados}\")\n        print(f\"🔄 Registros atualizados: {registros_atualizados}\")\n        \n        # Status final\n        total_final = OrdemServicoIxc.objects.count()\n        os_periodo_final = OrdemServicoIxc.objects.filter(\n            data_abertura__date__gte=inicio_periodo,\n            data_abertura__date__lte=fim_periodo\n        ).count()\n        \n        print(f\"\\n📈 === STATUS FINAL ===\")\n        print(f\"OS no banco total: {total_inicial} → {total_final} (+{total_final - total_inicial})\")\n        print(f\"OS do período: {os_periodo_banco} → {os_periodo_final} (+{os_periodo_final - os_periodo_banco})\")\n        \n        if os_periodo_final >= 56:\n            print(f\"🎉 META ATINGIDA! Temos {os_periodo_final} OS do período (meta: 56)\")\n        else:\n            faltando = 56 - os_periodo_final\n            print(f\"⚠️ Ainda faltam {faltando} OS para atingir a meta de 56\")\n        \n        return True\n        \n    except Exception as e:\n        print(f\"❌ ERRO: {e}\")\n        import traceback\n        traceback.print_exc()\n        return False\n\ndef analyze_period_details():\n    \"\"\"Analisa detalhes das OS do período\"\"\"\n    print(f\"\\n📊 === ANÁLISE DETALHADA DO PERÍODO ===\\n\")\n    \n    try:\n        from olt.models import OrdemServicoIxc\n        from datetime import date\n        from django.db.models import Count\n        \n        inicio_periodo = date(2025, 11, 1)\n        fim_periodo = date.today()\n        \n        os_periodo = OrdemServicoIxc.objects.filter(\n            data_abertura__date__gte=inicio_periodo,\n            data_abertura__date__lte=fim_periodo\n        )\n        \n        print(f\"📅 Período: {inicio_periodo} até {fim_periodo}\")\n        print(f\"📊 Total de OS no período: {os_periodo.count()}\")\n        \n        # Por data\n        print(f\"\\n📅 OS por data:\")\n        os_por_data = os_periodo.values('data_abertura__date').annotate(\n            count=Count('id')\n        ).order_by('-data_abertura__date')[:10]\n        \n        for item in os_por_data:\n            data_str = item['data_abertura__date'].strftime('%d/%m/%Y')\n            count = item['count']\n            print(f\"   {data_str}: {count} OS\")\n        \n        # Por assunto\n        print(f\"\\n🎯 OS por assunto:\")\n        os_por_assunto = os_periodo.values('assunto_nome').annotate(\n            count=Count('id')\n        ).order_by('-count')[:10]\n        \n        for item in os_por_assunto:\n            assunto = item['assunto_nome'] or '(Sem assunto)'\n            count = item['count']\n            print(f\"   {assunto}: {count} OS\")\n        \n        # Por status\n        print(f\"\\n📋 OS por status:\")\n        os_por_status = os_periodo.values('status').annotate(\n            count=Count('id')\n        ).order_by('-count')\n        \n        status_map = {'A': 'Aberta', 'F': 'Fechada', 'C': 'Cancelada'}\n        \n        for item in os_por_status:\n            status_key = item['status']\n            status_nome = status_map.get(status_key, status_key)\n            count = item['count']\n            print(f\"   {status_nome}: {count} OS\")\n        \n        return True\n        \n    except Exception as e:\n        print(f\"❌ Erro na análise: {e}\")\n        return False\n\nif __name__ == '__main__':\n    print(\"🚀 SINCRONIZAÇÃO DE OS POR PERÍODO\")\n    \n    sucesso = sync_period_os()\n    \n    if sucesso:\n        analyze_period_details()\n        print(\"\\n🎉 SINCRONIZAÇÃO POR PERÍODO CONCLUÍDA!\")\n    else:\n        print(\"\\n❌ SINCRONIZAÇÃO FALHOU\")\n        sys.exit(1)