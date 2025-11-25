#!/usr/bin/env python
"""
Script para testar e atualizar assuntos vazios nas OS
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_subjects_integration():
    """Testa a integração com assuntos do IXC"""
    print("=== TESTE DE INTEGRAÇÃO COM ASSUNTOS IXC ===")
    
    try:
        from olt.client_utils import IxcOSClient
        from olt.models import OrdemServicoIxc
        
        client = IxcOSClient()
        
        # 1. Testar busca de assuntos
        print("\n📋 === TESTANDO BUSCA DE ASSUNTOS ===")
        subjects = client.get_all_subjects()
        
        if subjects:
            print(f"✅ Encontrados {len(subjects)} assuntos")
            print("📌 Primeiros 10 assuntos:")
            for i, (id_assunto, nome) in enumerate(list(subjects.items())[:10], 1):
                print(f"   {i}. ID: {id_assunto} - Nome: {nome}")
        else:
            print("❌ Nenhum assunto encontrado")
            return False
        
        # 2. Verificar OS com assuntos vazios
        print(f"\n🔍 === VERIFICANDO OS COM ASSUNTOS VAZIOS ===")
        
        os_com_id_sem_nome = OrdemServicoIxc.objects.filter(
            id_assunto__isnull=False,
            assunto_nome__isnull=True
        ) | OrdemServicoIxc.objects.filter(
            id_assunto__isnull=False,
            assunto_nome=''
        )
        
        total_vazias = os_com_id_sem_nome.count()
        
        print(f"📊 Total de OS com ID de assunto mas nome vazio: {total_vazias}")
        
        if total_vazias > 0:
            print("🔧 Exemplos de OS que precisam ser atualizadas:")
            for os_obj in os_com_id_sem_nome[:5]:
                print(f"   - OS {os_obj.id_ixc}: ID Assunto {os_obj.id_assunto}, Nome: '{os_obj.assunto_nome}'")
        
        # 3. Testar busca de nome específico
        print(f"\n🎯 === TESTANDO BUSCA DE ASSUNTO ESPECÍFICO ===")
        
        if total_vazias > 0:
            os_exemplo = os_com_id_sem_nome.first()
            id_teste = os_exemplo.id_assunto
            
            print(f"Testando busca do assunto ID: {id_teste}")
            nome_encontrado = client.get_subject_name(id_teste)
            
            if nome_encontrado:
                print(f"✅ Nome encontrado: '{nome_encontrado}'")
            else:
                print(f"❌ Nome não encontrado para ID {id_teste}")
        
        # 4. Atualizar assuntos vazios
        print(f"\n🚀 === ATUALIZANDO ASSUNTOS VAZIOS ===")
        
        if total_vazias > 0:
            resultado = client.atualizar_assuntos_os_vazios()
            
            if resultado:
                print("✅ Atualização de assuntos concluída")
                
                # Verificar resultado
                os_ainda_vazias = OrdemServicoIxc.objects.filter(
                    id_assunto__isnull=False,
                    assunto_nome__isnull=True
                ) | OrdemServicoIxc.objects.filter(
                    id_assunto__isnull=False,
                    assunto_nome=''
                )
                
                print(f"📊 OS ainda com assuntos vazios: {os_ainda_vazias.count()}")
                print(f"✅ OS atualizadas: {total_vazias - os_ainda_vazias.count()}")
                
            else:
                print("❌ Falha na atualização de assuntos")
        else:
            print("✅ Nenhuma OS precisa de atualização")
        
        # 5. Estatísticas finais
        print(f"\n📈 === ESTATÍSTICAS FINAIS ===")
        
        total_os = OrdemServicoIxc.objects.count()
        os_com_assunto = OrdemServicoIxc.objects.filter(
            assunto_nome__isnull=False
        ).exclude(assunto_nome='').count()
        
        os_sem_assunto = total_os - os_com_assunto
        percentual_com_assunto = (os_com_assunto / total_os * 100) if total_os > 0 else 0
        
        print(f"📊 Total de OS: {total_os}")
        print(f"📊 OS com assunto preenchido: {os_com_assunto} ({percentual_com_assunto:.1f}%)")
        print(f"📊 OS sem assunto: {os_sem_assunto}")
        
        # 6. Exemplos de assuntos mais comuns
        print(f"\n🏆 === ASSUNTOS MAIS COMUNS ===")
        
        from django.db.models import Count
        
        assuntos_comuns = OrdemServicoIxc.objects.values('assunto_nome').annotate(
            count=Count('assunto_nome')
        ).filter(
            assunto_nome__isnull=False
        ).exclude(
            assunto_nome=''
        ).order_by('-count')[:10]
        
        for i, item in enumerate(assuntos_comuns, 1):
            nome = item['assunto_nome']
            quantidade = item['count']
            print(f"   {i}. {nome}: {quantidade} OS")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_specific_subject():
    """Testa busca de um assunto específico"""
    print("\n🔍 === TESTE DE ASSUNTO ESPECÍFICO ===")
    
    try:
        from olt.client_utils import IxcOSClient
        
        client = IxcOSClient()
        
        # Testar alguns IDs comuns
        ids_teste = [1, 2, 3, 4, 5, 8, 10]
        
        for id_assunto in ids_teste:
            nome = client.get_subject_name(id_assunto)
            if nome:
                print(f"   ID {id_assunto}: {nome}")
            else:
                print(f"   ID {id_assunto}: (não encontrado)")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

if __name__ == '__main__':
    print("🚀 INICIANDO TESTE DE ASSUNTOS IXC")
    
    # Teste principal
    sucesso = test_subjects_integration()
    
    if sucesso:
        # Teste específico
        test_specific_subject()
        print("\n🎉 TESTE COMPLETO FINALIZADO COM SUCESSO!")
    else:
        print("\n❌ TESTE FALHOU")
        sys.exit(1)