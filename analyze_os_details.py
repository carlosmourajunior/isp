#!/usr/bin/env python
"""
Análise detalhada de uma OS específica da API do IXC
Mostra TODOS os campos disponíveis para análise
"""
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def analyze_specific_os():
    """Analisa detalhadamente uma OS específica"""
    print("=== ANÁLISE DETALHADA DE OS ESPECÍFICA - API IXC ===")
    
    try:
        from olt.client_utils import IxcOSClient
        
        client = IxcOSClient()
        
        # 1. Obter lista de OS para escolher uma
        print("\n📋 === OBTENDO LISTA DE OS ===")
        response = client.listar_ordens_servico(page=1, rp=10)
        
        if not response or not response.get('registros'):
            print("❌ Nenhuma OS encontrada na API")
            return False
        
        registros = response.get('registros', [])
        print(f"✅ Encontradas {len(registros)} OS na primeira página")
        
        # Mostrar lista das OS disponíveis
        print("\n📌 OS Disponíveis para análise:")
        for i, os in enumerate(registros[:5], 1):  # Mostrar apenas as 5 primeiras
            id_ixc = os.get('id', 'N/A')
            protocolo = os.get('protocolo', 'N/A')
            status = os.get('status', 'N/A')
            assunto = os.get('assunto_nome', 'Sem assunto')
            print(f"   {i}. ID: {id_ixc} | Protocolo: {protocolo} | Status: {status}")
            print(f"      Assunto: {assunto[:60]}...")
        
        # Analisar a primeira OS em detalhes
        os_selecionada = registros[0]
        id_os = os_selecionada.get('id')
        
        print(f"\n🔍 === ANÁLISE DETALHADA DA OS ID: {id_os} ===")
        
        # 2. Obter OS específica (pode ter mais detalhes)
        print("\n📡 Obtendo detalhes completos via API específica...")
        os_detalhada = client.obter_ordem_servico(id_os)
        
        if os_detalhada:
            print("✅ Detalhes obtidos via endpoint específico")
            os_para_analise = os_detalhada
        else:
            print("⚠️ Usando dados da listagem geral")
            os_para_analise = os_selecionada
        
        # 3. Mostrar TODOS os campos disponíveis
        print(f"\n📊 === TODOS OS CAMPOS DISPONÍVEIS ({len(os_para_analise)} campos) ===")
        
        # Organizar campos por categoria
        campos_organizados = {
            'Identificação': ['id', 'protocolo', 'id_ticket'],
            'Status e Tipo': ['status', 'tipo', 'prioridade', 'origem_cadastro'],
            'Cliente': ['id_cliente', 'id_contrato_kit', 'id_login'],
            'Assunto': ['id_assunto', 'assunto_nome', 'dica_assinatura_digital'],
            'Técnico': ['id_tecnico', 'tecnico_nome', 'setor', 'id_atendente'],
            'Localização': ['endereco', 'bairro', 'id_cidade', 'complemento', 'referencia', 
                           'latitude', 'longitude', 'id_condominio', 'bloco', 'apartamento'],
            'Datas': ['data_abertura', 'data_inicio', 'data_agenda', 'data_agenda_final',
                     'data_hora_execucao', 'data_final', 'data_fechamento', 'data_prazo_limite',
                     'data_hora_analise', 'data_hora_encaminhado', 'data_hora_assumido',
                     'data_reservada', 'data_reagendar', 'data_prev_final', 'ultima_atualizacao'],
            'Mensagens': ['mensagem', 'mensagem_resposta', 'justificativa_sla_atrasado'],
            'Valores': ['valor_total', 'valor_outras_despesas', 'valor_unit_comissao', 'valor_total_comissao'],
            'Configurações': ['origem_endereco', 'origem_endereco_estrutura', 'melhor_horario_agenda',
                            'habilita_assinatura_cliente', 'status_assinatura', 'gera_comissao',
                            'liberado', 'impresso', 'preview'],
            'Workflow': ['id_wfl_param_os', 'id_wfl_tarefa', 'id_su_diagnostico'],
            'Outros': ['idx', 'status_pesquisa_satisfacao', 'status_sla', 'ids_login_regiao_manutencao',
                      'origem_os_aberta', 'regiao_manutencao', 'origem_change_endereco']
        }
        
        # Campos não categorizados
        campos_encontrados = set()
        
        for categoria, campos in campos_organizados.items():
            print(f"\n🏷️  {categoria.upper()}:")
            campos_nesta_categoria = []
            
            for campo in campos:
                if campo in os_para_analise:
                    valor = os_para_analise[campo]
                    campos_encontrados.add(campo)
                    campos_nesta_categoria.append((campo, valor))
            
            # Mostrar valores formatados
            for campo, valor in campos_nesta_categoria:
                valor_formatado = format_field_value(campo, valor)
                print(f"   {campo:25} = {valor_formatado}")
            
            if not campos_nesta_categoria:
                print("   (Nenhum campo desta categoria encontrado)")
        
        # Campos extras não categorizados
        campos_extras = set(os_para_analise.keys()) - campos_encontrados
        if campos_extras:
            print(f"\n🔍 CAMPOS EXTRAS NÃO CATEGORIZADOS:")
            for campo in sorted(campos_extras):
                valor = os_para_analise[campo]
                valor_formatado = format_field_value(campo, valor)
                print(f"   {campo:25} = {valor_formatado}")
        
        # 4. Análise específica do ASSUNTO
        print(f"\n🎯 === ANÁLISE ESPECÍFICA DO ASSUNTO ===")
        
        id_assunto = os_para_analise.get('id_assunto')
        assunto_nome = os_para_analise.get('assunto_nome')
        dica_assinatura = os_para_analise.get('dica_assinatura_digital')
        
        print(f"ID do Assunto: {id_assunto}")
        print(f"Nome do Assunto: {assunto_nome}")
        print(f"Dica Assinatura Digital: {dica_assinatura}")
        
        # Verificar se existem outros campos relacionados a assunto
        campos_assunto_possiveis = [
            'assunto', 'subject', 'categoria', 'category', 'servico', 'service',
            'tipo_servico', 'descricao_assunto', 'assunto_descricao'
        ]
        
        print("\n🔍 Outros campos que podem conter informação de assunto:")
        for campo in campos_assunto_possiveis:
            if campo in os_para_analise:
                valor = os_para_analise[campo]
                print(f"   {campo}: {valor}")
        
        # 5. Análise da mensagem (pode conter informações úteis)
        print(f"\n💬 === ANÁLISE DAS MENSAGENS ===")
        
        mensagem = os_para_analise.get('mensagem', '')
        mensagem_resposta = os_para_analise.get('mensagem_resposta', '')
        
        if mensagem:
            print(f"Mensagem ({len(mensagem)} caracteres):")
            print(f"   {mensagem[:200]}{'...' if len(mensagem) > 200 else ''}")
        else:
            print("Mensagem: (vazia)")
        
        if mensagem_resposta:
            print(f"Mensagem Resposta ({len(mensagem_resposta)} caracteres):")
            print(f"   {mensagem_resposta[:200]}{'...' if len(mensagem_resposta) > 200 else ''}")
        else:
            print("Mensagem Resposta: (vazia)")
        
        # 6. Recomendações para mapeamento
        print(f"\n💡 === RECOMENDAÇÕES PARA MAPEAMENTO ===")
        
        campos_importantes_faltando = []
        
        if not assunto_nome and not id_assunto:
            campos_importantes_faltando.append("ASSUNTO - Campo crítico não preenchido")
        
        if not os_para_analise.get('endereco'):
            campos_importantes_faltando.append("Endereço completo")
        
        if not os_para_analise.get('tecnico_nome') and not os_para_analise.get('id_tecnico'):
            campos_importantes_faltando.append("Informações do técnico")
        
        campos_extras_uteis = [
            'id_estrutura', 'id_filial', 'regiao_manutencao', 'setor'
        ]
        
        print("📋 Campos que deveriam ser adicionados ao modelo:")
        for campo in campos_extras_uteis:
            if campo in os_para_analise and os_para_analise[campo]:
                valor = os_para_analise[campo]
                print(f"   ✅ {campo}: {valor}")
        
        if campos_importantes_faltando:
            print("⚠️ Problemas identificados:")
            for problema in campos_importantes_faltando:
                print(f"   ❌ {problema}")
        
        # 7. Comparar com modelo atual
        print(f"\n🗄️ === COMPARAÇÃO COM MODELO ATUAL ===")
        
        from olt.models import OrdemServicoIxc
        campos_modelo_atual = [f.name for f in OrdemServicoIxc._meta.fields]
        
        print("Campos no modelo Django atual:")
        for campo in campos_modelo_atual:
            if campo not in ['id', 'sincronizado_em', 'criado_em']:
                print(f"   📋 {campo}")
        
        # 8. JSON completo para referência
        print(f"\n📄 === JSON COMPLETO DA OS (para referência) ===")
        print("(Salvando em arquivo para análise detalhada...)")
        
        # Salvar JSON completo em arquivo
        with open(f'/code/os_completa_{id_os}.json', 'w', encoding='utf-8') as f:
            json.dump(os_para_analise, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ JSON salvo em: /code/os_completa_{id_os}.json")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO NA ANÁLISE: {e}")
        import traceback
        traceback.print_exc()
        return False

def format_field_value(campo, valor):
    """Formata valor do campo para exibição"""
    if valor is None:
        return "None"
    elif valor == "":
        return "(vazio)"
    elif isinstance(valor, str) and len(valor) > 100:
        return f"'{valor[:100]}...'"
    else:
        return repr(valor)

def suggest_model_improvements():
    """Sugere melhorias no modelo baseado na análise"""
    print("\n🚀 === SUGESTÕES DE MELHORIAS NO MODELO ===")
    
    print("1. CAMPOS FALTANDO PARA ASSUNTOS:")
    print("   - Implementar busca de assuntos via API específica")
    print("   - Mapear dica_assinatura_digital")
    print("   - Considerar categoria/tipo de serviço")
    
    print("\n2. CAMPOS ADICIONAIS ÚTEIS:")
    campos_sugeridos = [
        ("id_estrutura", "IntegerField", "ID da estrutura/filial"),
        ("id_filial", "IntegerField", "ID da filial responsável"), 
        ("setor", "CharField", "Setor responsável"),
        ("regiao_manutencao", "CharField", "Região de manutenção"),
        ("origem_cadastro", "CharField", "Origem do cadastro"),
        ("melhor_horario_agenda", "CharField", "Melhor horário para agendamento"),
        ("latitude", "DecimalField", "Coordenada latitude"),
        ("longitude", "DecimalField", "Coordenada longitude"),
        ("dica_assinatura_digital", "TextField", "Dica para assinatura digital")
    ]
    
    for campo, tipo, descricao in campos_sugeridos:
        print(f"   - {campo} ({tipo}): {descricao}")
    
    print("\n3. MELHORIAS NO CLIENTE IXC:")
    print("   - Implementar cache de assuntos")
    print("   - Buscar dados de estrutura/filial")
    print("   - Mapear coordenadas geográficas")
    print("   - Melhorar tratamento de datas nulas")

if __name__ == '__main__':
    sucesso = analyze_specific_os()
    
    if sucesso:
        suggest_model_improvements()
        print("\n🎉 ANÁLISE COMPLETA FINALIZADA!")
        print("\n📁 Arquivos gerados:")
        print("   - os_completa_[ID].json - JSON completo da OS analisada")
    else:
        print("\n❌ ANÁLISE FALHOU")
        sys.exit(1)