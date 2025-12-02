#!/usr/bin/env python
"""
Test script for SystemUpdateLog functionality
"""

import os
import sys
import django
from datetime import datetime

# Setup Django environment
if __name__ == "__main__":
    # Add the project directory to the path
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_dir)
    
    # Setup Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
    django.setup()

from olt.models import SystemUpdateLog
from django.utils import timezone

def test_system_update_log():
    """Test SystemUpdateLog model and methods"""
    print("=" * 60)
    print("🧪 TESTE: SystemUpdateLog")
    print("=" * 60)
    
    # Create a test update log
    print("📝 Criando log de teste...")
    update_log = SystemUpdateLog.objects.create(
        tipo_atualizacao='manual',
        usuario='TestUser',
        status='em_progresso',
        job_id='test-123'
    )
    print(f"✅ Log criado: ID={update_log.id}")
    
    # Simulate success
    update_log.olt_system_ok = True
    update_log.port_occupation_ok = True
    update_log.onus_ok = True
    update_log.macs_ok = True
    update_log.clientes_ok = True
    update_log.status = 'concluido'
    update_log.concluido_em = timezone.now()
    update_log.duracao_segundos = 120
    update_log.sucessos = 5
    update_log.save()
    print(f"✅ Log atualizado para completo")
    
    # Test get_ultima_atualizacao_completa
    print("\n🔍 Testando get_ultima_atualizacao_completa...")
    ultima = SystemUpdateLog.get_ultima_atualizacao_completa()
    if ultima:
        print(f"✅ Última atualização encontrada:")
        print(f"   - Tipo: {ultima.tipo_atualizacao}")
        print(f"   - Usuário: {ultima.usuario}")
        print(f"   - Status: {ultima.status}")
        print(f"   - Data: {ultima.iniciado_em}")
        print(f"   - Duração: {ultima.duracao_segundos} segundos")
        print(f"   - Sucessos: {ultima.sucessos}/{ultima.total_etapas}")
    else:
        print("❌ Nenhuma atualização encontrada")
    
    # Test basic count
    print(f"\n📊 Total de logs: {SystemUpdateLog.objects.count()}")
    
    # List all logs
    print(f"\n📋 Todos os logs:")
    for log in SystemUpdateLog.objects.all().order_by('-iniciado_em')[:5]:
        print(f"   - {log.iniciado_em.strftime('%d/%m/%Y %H:%M')} | {log.tipo_atualizacao} | {log.status} | {log.usuario}")
    
    print(f"\n✅ Teste concluído!")

if __name__ == "__main__":
    test_system_update_log()