#!/usr/bin/env python
"""
Teste para validar dados das Ordens de Serviço já sincronizadas no banco
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_synced_data():
    """Testa e valida os dados já sincronizados no banco"""
    print("=== TESTE DOS DADOS SINCRONIZADOS NO BANCO ===")
    
    try:
        from olt.models import OrdemServicoIxc
        from django.db.models import Count, Sum, Q
        from datetime import datetime, timedelta
        
        # 1. Estatísticas gerais
        print("\n📊 === ESTATÍSTICAS GERAIS ===")
        total_os = OrdemServicoIxc.objects.count()
        print(f"Total de OS no banco: {total_os}")
        
        if total_os == 0:
            print("❌ Nenhuma OS encontrada no banco. Execute a sincronização primeiro.")
            return False
        
        # Por status
        stats_status = OrdemServicoIxc.objects.values('status').annotate(
            total=Count('id'),
            status_nome=Count('id')
        ).order_by('-total')
        
        print("\n📋 Por Status:")
        status_dict = dict(OrdemServicoIxc.STATUS_CHOICES)
        for stat in stats_status:
            status_nome = status_dict.get(stat['status'], stat['status'])
            print(f"   {status_nome}: {stat['total']} OS")
        
        # Por tipo
        stats_tipo = OrdemServicoIxc.objects.values('tipo').annotate(
            total=Count('id')
        ).order_by('-total')
        
        print("\n🔧 Por Tipo:")
        tipo_dict = dict(OrdemServicoIxc.TIPO_CHOICES)
        for stat in stats_tipo:
            tipo_nome = tipo_dict.get(stat['tipo'], stat['tipo'])
            print(f"   {tipo_nome}: {stat['total']} OS")
        
        # 2. Validação de integridade dos dados
        print("\n✅ === VALIDAÇÃO DE INTEGRIDADE ===")
        
        # OS com dados essenciais
        os_com_id_ixc = OrdemServicoIxc.objects.exclude(id_ixc__isnull=True).count()
        os_com_status = OrdemServicoIxc.objects.exclude(status__isnull=True).exclude(status='').count()
        os_com_tipo = OrdemServicoIxc.objects.exclude(tipo__isnull=True).exclude(tipo='').count()
        
        print(f"OS com ID IXC válido: {os_com_id_ixc}/{total_os} ({(os_com_id_ixc/total_os)*100:.1f}%)")
        print(f"OS com Status válido: {os_com_status}/{total_os} ({(os_com_status/total_os)*100:.1f}%)")
        print(f"OS com Tipo válido: {os_com_tipo}/{total_os} ({(os_com_tipo/total_os)*100:.1f}%)")
        
        # OS com datas
        os_com_data_abertura = OrdemServicoIxc.objects.exclude(data_abertura__isnull=True).count()
        os_com_data_agenda = OrdemServicoIxc.objects.exclude(data_agenda__isnull=True).count()
        os_com_data_execucao = OrdemServicoIxc.objects.exclude(data_execucao__isnull=True).count()
        
        print(f"OS com Data Abertura: {os_com_data_abertura}/{total_os} ({(os_com_data_abertura/total_os)*100:.1f}%)")
        print(f"OS com Data Agenda: {os_com_data_agenda}/{total_os} ({(os_com_data_agenda/total_os)*100:.1f}%)")
        print(f"OS com Data Execução: {os_com_data_execucao}/{total_os} ({(os_com_data_execucao/total_os)*100:.1f}%)")
        
        # OS com informações do cliente/técnico
        os_com_cliente = OrdemServicoIxc.objects.exclude(id_cliente__isnull=True).count()
        os_com_tecnico = OrdemServicoIxc.objects.exclude(id_tecnico__isnull=True).count()
        os_com_assunto = OrdemServicoIxc.objects.exclude(assunto_nome__isnull=True).exclude(assunto_nome='').count()
        
        print(f"OS com ID Cliente: {os_com_cliente}/{total_os} ({(os_com_cliente/total_os)*100:.1f}%)")
        print(f"OS com ID Técnico: {os_com_tecnico}/{total_os} ({(os_com_tecnico/total_os)*100:.1f}%)")
        print(f"OS com Assunto: {os_com_assunto}/{total_os} ({(os_com_assunto/total_os)*100:.1f}%)")
        
        # 3. Análise de valores financeiros
        print("\n💰 === ANÁLISE FINANCEIRA ===")
        
        os_com_valor = OrdemServicoIxc.objects.exclude(valor_total__isnull=True).exclude(valor_total=0)
        total_com_valor = os_com_valor.count()
        
        if total_com_valor > 0:
            valor_total = os_com_valor.aggregate(Sum('valor_total'))['valor_total__sum']
            valor_medio = valor_total / total_com_valor if total_com_valor > 0 else 0
            
            print(f"OS com valor financeiro: {total_com_valor}/{total_os} ({(total_com_valor/total_os)*100:.1f}%)")
            print(f"Valor total das OS: R$ {valor_total:,.2f}")
            print(f"Valor médio por OS: R$ {valor_medio:,.2f}")
            
            # Valores por status
            print("\n💰 Valores por Status:")
            for status_code, status_nome in OrdemServicoIxc.STATUS_CHOICES:
                valor_status = OrdemServicoIxc.objects.filter(
                    status=status_code
                ).exclude(
                    valor_total__isnull=True
                ).aggregate(Sum('valor_total'))['valor_total__sum'] or 0
                
                if valor_status > 0:
                    print(f"   {status_nome}: R$ {valor_status:,.2f}")
        else:
            print("Nenhuma OS com valor financeiro encontrada")
        
        # 4. Top assuntos
        print("\n🎯 === TOP 10 ASSUNTOS ===")
        
        top_assuntos = OrdemServicoIxc.objects.filter(
            assunto_nome__isnull=False
        ).exclude(
            assunto_nome=''
        ).values('assunto_nome').annotate(
            total=Count('id')
        ).order_by('-total')[:10]
        
        for i, assunto in enumerate(top_assuntos, 1):
            print(f"{i:2d}. {assunto['assunto_nome'][:50]}: {assunto['total']} OS")
        
        # 5. Análise temporal
        print("\n📅 === ANÁLISE TEMPORAL ===")
        
        hoje = datetime.now().date()
        
        # OS por período
        os_hoje = OrdemServicoIxc.objects.filter(data_abertura__date=hoje).count()
        os_ultima_semana = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte=hoje - timedelta(days=7)
        ).count()
        os_ultimo_mes = OrdemServicoIxc.objects.filter(
            data_abertura__date__gte=hoje - timedelta(days=30)
        ).count()
        
        print(f"OS abertas hoje: {os_hoje}")
        print(f"OS abertas na última semana: {os_ultima_semana}")
        print(f"OS abertas no último mês: {os_ultimo_mes}")
        
        # 6. Dados de exemplo
        print("\n📋 === EXEMPLO DE DADOS SINCRONIZADOS ===")
        
        os_exemplo = OrdemServicoIxc.objects.filter(
            assunto_nome__isnull=False
        ).exclude(assunto_nome='').first()
        
        if os_exemplo:
            print(f"Exemplo de OS sincronizada:")
            print(f"   ID IXC: {os_exemplo.id_ixc}")
            print(f"   Protocolo: {os_exemplo.protocolo}")
            print(f"   Status: {os_exemplo.get_status_display()}")
            print(f"   Tipo: {os_exemplo.get_tipo_display()}")
            print(f"   Assunto: {os_exemplo.assunto_nome}")
            print(f"   Data Abertura: {os_exemplo.data_abertura}")
            print(f"   Valor: R$ {os_exemplo.valor_total or 0}")
            print(f"   Sincronizado em: {os_exemplo.sincronizado_em}")
        
        # 7. Verificação de possíveis problemas
        print("\n⚠️  === VERIFICAÇÃO DE PROBLEMAS ===")
        
        problemas = []
        
        # OS sem ID IXC
        os_sem_id = OrdemServicoIxc.objects.filter(id_ixc__isnull=True).count()
        if os_sem_id > 0:
            problemas.append(f"{os_sem_id} OS sem ID IXC")
        
        # OS sem data de abertura
        os_sem_data = OrdemServicoIxc.objects.filter(data_abertura__isnull=True).count()
        if os_sem_data > 0:
            problemas.append(f"{os_sem_data} OS sem data de abertura")
        
        # OS com status inválido
        os_status_invalido = OrdemServicoIxc.objects.exclude(
            status__in=[choice[0] for choice in OrdemServicoIxc.STATUS_CHOICES]
        ).count()
        if os_status_invalido > 0:
            problemas.append(f"{os_status_invalido} OS com status inválido")
        
        if problemas:
            print("Problemas encontrados:")
            for problema in problemas:
                print(f"   ❌ {problema}")
        else:
            print("✅ Nenhum problema crítico encontrado nos dados")
        
        print(f"\n🎉 VALIDAÇÃO CONCLUÍDA - {total_os} OS analisadas")
        return True
        
    except Exception as e:
        print(f"❌ ERRO NA VALIDAÇÃO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_synced_data()