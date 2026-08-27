#!/usr/bin/env python
"""
Script para adicionar IPs permitidos via terminal
Uso: docker-compose exec web python add_ip.py IP_ADDRESS "DESCRIPTION"
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.models import AllowedIP

def add_ip(ip_address, description="IP adicionado via terminal"):
    """Adiciona um IP à lista de permitidos"""
    try:
        # Verifica se já existe
        if AllowedIP.objects.filter(ip_address=ip_address).exists():
            print(f"❌ IP {ip_address} já existe na lista!")
            return False
        
        # Cria o IP
        allowed_ip = AllowedIP.objects.create(
            ip_address=ip_address,
            description=description,
            is_active=True
        )
        
        print(f"✅ IP {ip_address} adicionado com sucesso!")
        print(f"📝 Descrição: {description}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao adicionar IP: {e}")
        return False

def list_ips():
    """Lista todos os IPs permitidos"""
    ips = AllowedIP.objects.all().order_by('ip_address')
    print("\n📋 IPs PERMITIDOS:")
    print("=" * 50)
    for ip in ips:
        status = "🟢 ATIVO" if ip.is_active else "🔴 INATIVO"
        print(f"{status} {ip.ip_address} - {ip.description}")
    print(f"\nTotal: {ips.count()} IPs")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("💡 USO:")
        print("  python add_ip.py IP_ADDRESS [DESCRIPTION]")
        print("  python add_ip.py list")
        print("\n📌 EXEMPLOS:")
        print('  python add_ip.py 192.168.1.100 "Meu computador"')
        print('  python add_ip.py 10.0.0.0/8 "Rede interna"')
        print('  python add_ip.py list')
        sys.exit(1)
    
    if sys.argv[1].lower() == 'list':
        list_ips()
    else:
        ip_address = sys.argv[1]
        description = sys.argv[2] if len(sys.argv) > 2 else f"IP {ip_address} adicionado via terminal"
        add_ip(ip_address, description)