#!/usr/bin/env python
"""
Script para debugar o erro do scheduler
"""
import os
import sys
import django
import traceback

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code' if os.path.exists('/code') else os.path.dirname(os.path.abspath(__file__)))

# Criar diretório de logs se não existir
log_dir = r'E:\code\logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

django.setup()


def test_rq_execution():
    """Testa execução via RQ"""
    print("\n" + "=" * 60)
    print("🔍 TESTE 2: Execução via RQ")
    print("=" * 60)
    
    try:
        import django_rq
        from olt.tasks import scheduled_complete_update_task
        
        # Obter fila
        queue = django_rq.get_queue('default')
        print(f"\n📊 Fila conectada: {queue}")
        print(f"📊 Jobs na fila: {queue.count}")
        
        # Tentar agendar
        print("\n🚀 Agendando task via RQ...")
        job = queue.enqueue(
            scheduled_complete_update_task,
            user="Teste RQ",
            menu_item="Debug RQ Test",
            job_timeout=3600  # 1 hora de timeout
        )
        
        print(f"\n✅ Task agendada!")
        print(f"   Job ID: {job.id}")
        print(f"   Status inicial: {job.get_status()}")
        
        # Aguardar processamento
        import time
        print("\n⏳ Aguardando 10 segundos para processar...")
        for i in range(10):
            time.sleep(1)
            job.refresh()
            status = job.get_status()
            print(f"   [{i+1}/10] Status: {status}")
            
            if status == 'finished':
                print(f"\n✅ Job completado com sucesso!")
                print(f"   Resultado: {job.result}")
                return True
            elif status == 'failed':
                print(f"\n❌ Job falhou!")
                print(f"   Erro: {job.exc_info}")
                return False
        
        print(f"\n⏰ Timeout - Job ainda em processamento")
        print(f"   Status final: {job.get_status()}")
        return None
        
    except Exception as e:
        print(f"\n❌ Erro ao testar via RQ:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensagem: {str(e)}")
        print(f"\n📋 Traceback completo:")
        traceback.print_exc()
        return False

def check_redis_connection():
    """Verifica conexão com Redis"""
    print("\n" + "=" * 60)
    print("🔍 TESTE 0: Conexão Redis")
    print("=" * 60)
    
    try:
        import redis
        from django.conf import settings
        
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        print(f"\n📡 Conectando ao Redis: {redis_url}")
        
        r = redis.from_url(redis_url)
        r.ping()
        
        print(f"✅ Redis conectado com sucesso!")
        print(f"   Versão: {r.info()['redis_version']}")
        print(f"   Banco: {r.connection_pool.connection_kwargs.get('db', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao conectar no Redis:")
        print(f"   Tipo: {type(e).__name__}")
        print(f"   Mensagem: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n🧪 DEBUGANDO SCHEDULER - Sistema ISP OLT")
    print("=" * 60)
    
    # Teste 0: Redis
    redis_ok = check_redis_connection()
    
    if not redis_ok:
        print("\n⚠️  ATENÇÃO: Redis não está acessível!")
        print("   Execute: docker compose ps")
        print("   Verifique se o container 'redis' está rodando")
        sys.exit(1)
    
    # Teste via RQ
    rq_ok = test_rq_execution()
    print("\n" + "=" * 60)
    print("📊 RESUMO DO TESTE RQ")
    print("=" * 60)
    print(f"   Redis:           {'✅ OK' if redis_ok else '❌ FALHOU'}")
    print(f"   Execução RQ:     {'✅ OK' if rq_ok else '❌ FALHOU' if rq_ok is False else '⏰ TIMEOUT'}")
    print("=" * 60)
    if not rq_ok:
        print("\n💡 DIAGNÓSTICO: A task falhou via RQ")
        print("   Possíveis causas:")
        print("   1. Worker RQ não tem as mesmas permissões")
        print("   2. Configuração do RQ está incorreta")
        print("   3. Middleware Django está bloqueando")
    else:
        print("\n✅ SUCESSO: Task via RQ funcionando corretamente!")
