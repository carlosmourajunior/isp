#!/usr/bin/env python
"""
Script para limpar cache de assuntos e testar novamente
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def clear_cache_and_test():
    """Limpa cache e testa assuntos novamente"""
    print("=== LIMPEZA DE CACHE E TESTE ===")
    
    try:
        from django.core.cache import cache
        from olt.client_utils import IxcOSClient
        from olt.models import OrdemServicoIxc
        
        # 1. Limpar cache
        print("🧹 Limpando cache de assuntos...")
        cache.delete('ixc_subjects_cache')
        
        # 2. Testar busca de assuntos
        client = IxcOSClient()
        
        print("\n📋 Testando busca de assuntos (sem cache)...")
        subjects = client.get_all_subjects()
        
        print(f"✅ Total de assuntos: {len(subjects)}")
        
        # 3. Mostrar todos os assuntos
        print("\n📌 TODOS OS ASSUNTOS DISPONÍVEIS:")
        for id_assunto in sorted([int(k) for k in subjects.keys()]):
            nome = subjects[str(id_assunto)]
            print(f"   ID {id_assunto:2d}: {nome}")
        
        # 4. Testar assuntos específicos que estavam faltando
        print(f"\n🎯 TESTANDO ASSUNTOS QUE ESTAVAM FALTANDO:")
        
        assuntos_teste = [1, 2, 3, 4, 5]
        for id_teste in assuntos_teste:
            nome = client.get_subject_name(id_teste)
            if nome:
                print(f"   ✅ ID {id_teste}: {nome}")
            else:
                print(f"   ❌ ID {id_teste}: não encontrado")
        
        # 5. Atualizar OS com assuntos vazios
        print(f"\n🚀 ATUALIZANDO OS COM ASSUNTOS VAZIOS...")
        
        # Verificar quantas OS têm assuntos vazios
        os_vazias = OrdemServicoIxc.objects.filter(
            id_assunto__isnull=False,
            assunto_nome__isnull=True
        ) | OrdemServicoIxc.objects.filter(
            id_assunto__isnull=False,
            assunto_nome=''
        )
        
        print(f"📊 OS com assuntos vazios: {os_vazias.count()}")
        
        if os_vazias.count() > 0:
            # Mostrar exemplos
            print("📋 Exemplos de OS que serão atualizadas:")
            for os_obj in os_vazias[:5]:
                print(f"   - OS {os_obj.id_ixc}: ID Assunto {os_obj.id_assunto}")
            
            # Executar atualização
            resultado = client.atualizar_assuntos_os_vazios()
            
            if resultado:
                print("✅ Atualização concluída")
                
                # Verificar resultado
                os_ainda_vazias = OrdemServicoIxc.objects.filter(
                    id_assunto__isnull=False,
                    assunto_nome__isnull=True
                ) | OrdemServicoIxc.objects.filter(
                    id_assunto__isnull=False,
                    assunto_nome=''
                )
                
                atualizadas = os_vazias.count() - os_ainda_vazias.count()
                print(f"📊 OS atualizadas: {atualizadas}")
                print(f"📊 OS ainda vazias: {os_ainda_vazias.count()}")
            else:
                print("❌ Falha na atualização")
        
        # 6. Estatísticas finais
        print(f"\n📈 ESTATÍSTICAS FINAIS:")
        
        total_os = OrdemServicoIxc.objects.count()
        os_com_assunto = OrdemServicoIxc.objects.filter(
            assunto_nome__isnull=False
        ).exclude(assunto_nome='').count()
        
        percentual = (os_com_assunto / total_os * 100) if total_os > 0 else 0
        
        print(f"📊 Total de OS: {total_os}")
        print(f"📊 OS com assunto: {os_com_assunto} ({percentual:.1f}%)")
        
        # 7. Top assuntos
        print(f"\n🏆 TOP ASSUNTOS MAIS USADOS:")
        
        from django.db.models import Count
        
        top_assuntos = OrdemServicoIxc.objects.values('assunto_nome', 'id_assunto').annotate(
            count=Count('id')
        ).filter(
            assunto_nome__isnull=False
        ).exclude(
            assunto_nome=''
        ).order_by('-count')[:10]
        
        for i, item in enumerate(top_assuntos, 1):
            nome = item['assunto_nome']
            id_assunto = item['id_assunto']
            quantidade = item['count']
            print(f"   {i}. {nome} (ID {id_assunto}): {quantidade} OS")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("🚀 INICIANDO LIMPEZA DE CACHE E TESTE")
    
    sucesso = clear_cache_and_test()
    
    if sucesso:
        print("\n🎉 TESTE CONCLUÍDO COM SUCESSO!")
    else:
        print("\n❌ TESTE FALHOU")
        sys.exit(1)