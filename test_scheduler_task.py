#!/usr/bin/env python
"""
Script para testar a task do scheduler manualmente
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code' if os.path.exists('/code') else os.path.dirname(os.path.abspath(__file__)))

# Criar diretório de logs se não existir
log_dir = r'E:\code\logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

django.setup()

def test_scheduler_task():
    """Testa a task do scheduler"""
    print("🔍 Testando task do scheduler...")
    
    try:
        import django_rq
        from olt.tasks import scheduled_complete_update_task
        
        # Obter fila
        queue = django_rq.get_queue('default')
        
        print(f"📊 Fila conectada: {queue}")
        print(f"📊 Jobs na fila: {queue.count}")
        
        # Agendar task
        print("\n🚀 Agendando task scheduled_complete_update_task...")
        job = queue.enqueue(
            scheduled_complete_update_task,
            user="Teste Manual",
            menu_item="Teste de Scheduler",
            job_timeout=3600
        )
        
        print(f"✅ Task agendada com sucesso!")
        print(f"   Job ID: {job.id}")
        print(f"   Status: {job.get_status()}")
        print(f"   Criado em: {job.created_at}")
        
        # Aguardar um pouco e verificar status
        import time
        print("\n⏳ Aguardando 5 segundos...")
        time.sleep(5)
        
        job.refresh()
        print(f"\n📊 Status atualizado:")
        print(f"   Status: {job.get_status()}")
        print(f"   Meta: {job.meta}")
        
        if job.get_status() == 'failed':
            print(f"\n❌ Job falhou!")
            print(f"   Erro: {job.exc_info}")
        elif job.get_status() in ['queued', 'started']:
            print(f"\n✅ Job está sendo processado!")
            print(f"\n💡 Para acompanhar o progresso:")
            print(f"   docker compose -f docker-compose.scheduler.yml logs -f")
            print(f"   OU")
            print(f"   docker compose logs -f rq_worker")
        
    except Exception as e:
        print(f"❌ Erro ao testar task: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_scheduler_task()
