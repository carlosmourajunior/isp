#!/usr/bin/env python3
"""
Script para monitorar o progresso de um job RQ específico
"""
import os
import sys
import django
import time

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code' if os.path.exists('/code') else os.path.dirname(os.path.abspath(__file__)))
django.setup()

import django_rq
from datetime import datetime

def monitor_job(job_id, max_time=600):
    """
    Monitora um job específico até completar ou dar timeout
    """
    print(f"🔍 MONITORANDO JOB: {job_id}")
    print(f"⏰ Timeout máximo: {max_time}s ({max_time//60}m)")
    print("=" * 60)
    
    try:
        # Conectar ao Redis e obter o job
        queue = django_rq.get_queue('default')
        from rq import get_current_connection
        connection = get_current_connection()
        
        from rq.job import Job
        job = Job.fetch(job_id, connection=connection)
        
        start_time = time.time()
        last_status = None
        last_step = None
        
        while time.time() - start_time < max_time:
            try:
                # Atualizar status do job
                job.refresh()
                current_status = job.get_status()
                current_step = job.meta.get('current_step', 'N/A')
                
                # Mostrar mudanças
                if current_status != last_status or current_step != last_step:
                    elapsed = int(time.time() - start_time)
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{timestamp}] +{elapsed:3d}s | Status: {current_status:8s} | {current_step}")
                    
                    last_status = current_status
                    last_step = current_step
                
                # Verificar se terminou
                if current_status == 'finished':
                    print(f"\n✅ JOB COMPLETO!")
                    print(f"   Resultado: {job.result}")
                    if hasattr(job, 'meta') and job.meta.get('resultados'):
                        print(f"   Resultados detalhados:")
                        for nome, res in job.meta['resultados'].items():
                            status_emoji = "✅" if res['status'] else "❌"
                            print(f"     {status_emoji} {nome}")
                    return True
                    
                elif current_status == 'failed':
                    print(f"\n❌ JOB FALHOU!")
                    print(f"   Erro: {job.exc_info}")
                    return False
                
            except Exception as e:
                print(f"   ⚠️ Erro ao verificar job: {e}")
            
            time.sleep(5)  # Aguardar 5 segundos
        
        print(f"\n⏰ TIMEOUT: Job ainda executando após {max_time}s")
        print(f"   Status final: {job.get_status()}")
        return None
        
    except Exception as e:
        print(f"❌ Erro ao monitorar job: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python monitor_job.py <JOB_ID>")
        print("Exemplo: python monitor_job.py fc9fe74e-0eea-4554-b5d3-b17662dd85f2")
        sys.exit(1)
    
    job_id = sys.argv[1]
    result = monitor_job(job_id, max_time=900)  # 15 minutos
    
    if result is True:
        print("\n🎉 Sucesso!")
    elif result is False:
        print("\n💥 Falha!")
    else:
        print("\n⏰ Timeout!")