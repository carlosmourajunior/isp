#!/usr/bin/env python
"""
Script para executar sincronização completa de OS do IXC
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def sync_all_os():
    """Executa sincronização completa de todas as OS"""
    print("=== SINCRONIZAÇÃO COMPLETA DE ORDENS DE SERVIÇO IXC ===")
    
    try:
        from olt.client_utils import IxcOSClient
        from olt.models import OrdemServicoIxc
        from django_rq import get_queue
        import time
        
        # 1. Status inicial
        print(f"\n📊 === STATUS INICIAL ===")
        total_banco_inicial = OrdemServicoIxc.objects.count()
        print(f"OS no banco antes da sincronização: {total_banco_inicial}")
        
        # 2. Testar conexão com API
        print(f"\n🔍 === TESTANDO CONEXÃO COM API ===")
        client = IxcOSClient()
        
        response = client.listar_ordens_servico(page=1, rp=1)
        if not response:
            print("❌ Erro ao conectar com API do IXC")
            return False
        
        total_api = int(response.get('total', 0))
        print(f"✅ Conexão OK - Total de OS na API: {total_api}")
        
        # Calcular páginas necessárias
        paginas_necessarias = (total_api // 100) + (1 if total_api % 100 > 0 else 0)
        print(f"📄 Páginas necessárias: {paginas_necessarias}")
        
        # Estimar tempo
        tempo_estimado_min = paginas_necessarias * 2  # ~2 minutos por página
        print(f"⏱️ Tempo estimado: {tempo_estimado_min} minutos")
        
        # 3. Opções de sincronização
        print(f"\n🎯 === OPÇÕES DE SINCRONIZAÇÃO ===")
        print("1. Sincronização LIMITADA (10 páginas - ~1000 OS)")
        print("2. Sincronização MÉDIA (50 páginas - ~5000 OS)")  
        print("3. Sincronização COMPLETA (todas as páginas - todas as OS)")
        print("4. Sincronização VIA TASK (background)")
        
        opcao = input("\nEscolha uma opção (1-4): ").strip()
        
        if opcao == "1":
            print(f"\n🚀 === SINCRONIZAÇÃO LIMITADA (10 páginas) ===")
            sucesso = client.sincronizar_ordens_servico(limite_paginas=10)
            
        elif opcao == "2":
            print(f"\n🚀 === SINCRONIZAÇÃO MÉDIA (50 páginas) ===")
            sucesso = client.sincronizar_ordens_servico(limite_paginas=50)
            
        elif opcao == "3":
            print(f"\n🚀 === SINCRONIZAÇÃO COMPLETA (TODAS AS PÁGINAS) ===")
            print("⚠️ ATENÇÃO: Isso pode demorar mais de 1 hora!")
            confirma = input("Confirma a sincronização completa? (s/N): ").strip().lower()
            
            if confirma == 's':
                sucesso = client.sincronizar_ordens_servico(limite_paginas=None)
            else:
                print("❌ Sincronização cancelada")
                return False
                
        elif opcao == "4":
            print(f"\n🚀 === SINCRONIZAÇÃO VIA TASK (BACKGROUND) ===")
            print("1. Limitada (10 páginas)")
            print("2. Média (50 páginas)")
            print("3. Completa (todas)")
            
            task_opcao = input("Escolha (1-3): ").strip()
            
            queue = get_queue('default')
            
            if task_opcao == "1":
                job = queue.enqueue(
                    'olt.tasks.sincronizar_os_task',
                    limite_paginas=10,
                    user="Script",
                    job_timeout=1800
                )
                print(f"✅ Task limitada iniciada - Job ID: {job.id}")
                
            elif task_opcao == "2":
                job = queue.enqueue(
                    'olt.tasks.sincronizar_os_task',
                    limite_paginas=50,
                    user="Script", 
                    job_timeout=3600
                )
                print(f"✅ Task média iniciada - Job ID: {job.id}")
                
            elif task_opcao == "3":
                job = queue.enqueue(
                    'olt.tasks.sincronizar_os_task',
                    limite_paginas=None,
                    sync_all=True,
                    user="Script",
                    job_timeout=7200  # 2 horas
                )
                print(f"✅ Task completa iniciada - Job ID: {job.id}")
                
            else:
                print("❌ Opção inválida")
                return False
            
            # Monitorar job por alguns segundos
            print(f"\n📊 Monitorando job por 30 segundos...")
            for i in range(6):
                time.sleep(5)
                job.refresh()
                status = job.get_status()
                meta = getattr(job, 'meta', {})
                current_step = meta.get('current_step', 'Iniciando...')
                
                print(f"   [{i*5+5}s] Status: {status} - {current_step}")
                
                if status in ['finished', 'failed']:
                    break
            
            print(f"✅ Task iniciada com sucesso - continue monitorando via dashboard")
            return True
            
        else:
            print("❌ Opção inválida")
            return False
        
        # 4. Verificar resultado (para sync direto)
        if opcao in ["1", "2", "3"]:
            print(f"\n📊 === RESULTADO DA SINCRONIZAÇÃO ===")
            
            if sucesso:
                total_banco_final = OrdemServicoIxc.objects.count()
                novas_os = total_banco_final - total_banco_inicial
                
                print(f"✅ Sincronização concluída com sucesso!")
                print(f"📊 OS no banco antes: {total_banco_inicial}")
                print(f"📊 OS no banco depois: {total_banco_final}")
                print(f"📊 Novas OS sincronizadas: {novas_os}")
                
                if total_banco_final < total_api:
                    faltando = total_api - total_banco_final
                    percentual = (total_banco_final / total_api) * 100
                    print(f"⚠️ Ainda faltam {faltando} OS ({percentual:.1f}% sincronizado)")
                else:
                    print(f"🎉 TODAS as OS foram sincronizadas!")
                
            else:
                print(f"❌ Erro na sincronização")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_sync_status():
    """Verifica status atual da sincronização"""
    print(f"\n📊 === STATUS ATUAL ===")
    
    try:
        from olt.models import OrdemServicoIxc
        from olt.client_utils import IxcOSClient
        from datetime import date
        
        # Status do banco
        total_banco = OrdemServicoIxc.objects.count()
        print(f"Total de OS no banco: {total_banco}")
        
        # OS recentes
        hoje = date.today()
        os_hoje = OrdemServicoIxc.objects.filter(data_abertura__date=hoje).count()
        print(f"OS abertas hoje: {os_hoje}")
        
        # Status da API
        client = IxcOSClient()
        response = client.listar_ordens_servico(page=1, rp=1)
        
        if response:
            total_api = int(response.get('total', 0))
            print(f"Total de OS na API: {total_api}")
            
            if total_banco < total_api:
                faltando = total_api - total_banco
                percentual = (total_banco / total_api) * 100
                print(f"⚠️ Faltando: {faltando} OS ({percentual:.1f}% sincronizado)")
            else:
                print(f"✅ Sincronização completa")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == '__main__':
    print("🚀 SINCRONIZAÇÃO DE OS IXC")
    
    # Verificar status primeiro
    check_sync_status()
    
    # Executar sincronização
    sucesso = sync_all_os()
    
    if sucesso:
        print("\n🎉 PROCESSO CONCLUÍDO!")
    else:
        print("\n❌ PROCESSO FALHOU")
        sys.exit(1)