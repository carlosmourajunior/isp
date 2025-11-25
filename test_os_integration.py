#!/usr/bin/env python
"""
Script para testar a integração com Ordens de Serviço do IXC
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_os_integration():
    """Testa a integração com OS do IXC"""
    print("=== TESTE DE INTEGRAÇÃO - ORDENS DE SERVIÇO IXC ===")
    
    try:
        # Testar imports
        from olt.models import OrdemServicoIxc
        from olt.client_utils import IxcOSClient
        from olt.serializers import OrdemServicoIxcSerializer, OrdemServicoResumoSerializer
        
        print("✅ Imports realizados com sucesso")
        
        # Verificar modelo
        print(f"📊 Modelo OrdemServicoIxc: {OrdemServicoIxc._meta.verbose_name}")
        print(f"📊 Total de campos: {len(OrdemServicoIxc._meta.fields)}")
        
        # Testar cliente IXC (sem fazer requisições reais)
        try:
            client = IxcOSClient()
            print(f"🔗 Cliente IXC inicializado - Host: {client.host}")
            print(f"🔗 Base URL: {client.base_url}")
        except Exception as e:
            print(f"⚠️ Erro ao inicializar cliente IXC: {e}")
        
        # Verificar banco de dados
        total_os = OrdemServicoIxc.objects.count()
        print(f"📈 Total de OS no banco: {total_os}")
        
        # Testar serializers
        print("🔧 Testando serializers...")
        if total_os > 0:
            primeira_os = OrdemServicoIxc.objects.first()
            serializer = OrdemServicoIxcSerializer(primeira_os)
            print(f"✅ Serializer completo testado - ID: {serializer.data.get('id_ixc')}")
            
            resumo_serializer = OrdemServicoResumoSerializer(primeira_os)
            print(f"✅ Serializer resumo testado - Protocolo: {resumo_serializer.data.get('protocolo')}")
        else:
            print("ℹ️ Nenhuma OS no banco para testar serializers")
        
        print("\n=== ESTATÍSTICAS DO MODELO ===")
        print(f"Status disponíveis: {[choice[1] for choice in OrdemServicoIxc.STATUS_CHOICES]}")
        print(f"Tipos disponíveis: {[choice[1] for choice in OrdemServicoIxc.TIPO_CHOICES]}")
        print(f"Prioridades disponíveis: {[choice[1] for choice in OrdemServicoIxc.PRIORIDADE_CHOICES]}")
        
        print("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        return True
        
    except Exception as e:
        print(f"❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_os_integration()