#!/usr/bin/env python
"""
Script para testar a configuração de IP whitelist.
Este script simula requests de diferentes IPs para verificar se o middleware está funcionando.
"""

import os
import sys
import django
from django.test import RequestFactory
from django.conf import settings

# Adiciona o diretório do projeto ao Python path
project_path = os.path.dirname(os.path.abspath(__file__))
if project_path not in sys.path:
    sys.path.append(project_path)

# Configura o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from isp.middleware import IPWhitelistMiddleware


def test_ip_whitelist():
    """
    Testa o middleware de IP whitelist com diferentes IPs.
    """
    print("=== Teste do Middleware de IP Whitelist ===\n")
    
    # Cria uma instância do middleware
    def dummy_get_response(request):
        return "OK"
    
    middleware = IPWhitelistMiddleware(dummy_get_response)
    factory = RequestFactory()
    
    # Lista de IPs para testar (adaptado para Docker)
    test_ips = [
        ('127.0.0.1', True, 'Localhost IPv4'),
        ('::1', True, 'Localhost IPv6'),
        ('177.22.126.77', True, 'Servidor'),
        ('172.17.0.1', True, 'Docker bridge IP'),
        ('192.168.1.100', True, 'IP privado autorizado'),
        ('10.0.0.1', True, 'IP privado autorizado'),
        ('203.0.113.1', False, 'IP público não autorizado'),
        ('8.8.8.8', False, 'IP público não autorizado'),
    ]
    
    print("IPs configurados como permitidos:")
    for ip in settings.ALLOWED_IPS:
        print(f"  - {ip}")
    print()
    
    for ip, should_be_allowed, description in test_ips:
        request = factory.get('/')
        request.META['REMOTE_ADDR'] = ip
        
        is_allowed = middleware.is_ip_allowed(request)
        status = "✅ PERMITIDO" if is_allowed else "❌ BLOQUEADO"
        expected = "✅" if should_be_allowed else "❌"
        
        print(f"{status} | IP: {ip:<15} | {description}")
        
        if is_allowed != should_be_allowed:
            print(f"  ⚠️  ATENÇÃO: Resultado inesperado! Esperado: {expected}")
    
    print("\n=== Teste de IPs com X-Forwarded-For ===")
    
    # Testa com header X-Forwarded-For (comum em proxies/load balancers)
    request = factory.get('/')
    request.META['HTTP_X_FORWARDED_FOR'] = '177.22.126.77, 192.168.1.1'
    request.META['REMOTE_ADDR'] = '192.168.1.1'
    
    is_allowed = middleware.is_ip_allowed(request)
    client_ip = middleware.get_client_ip(request)
    
    print(f"X-Forwarded-For: 177.22.126.77, 192.168.1.1")
    print(f"Remote-Addr: 192.168.1.1")
    print(f"IP detectado: {client_ip}")
    print(f"Resultado: {'✅ PERMITIDO' if is_allowed else '❌ BLOQUEADO'}")


if __name__ == '__main__':
    try:
        test_ip_whitelist()
    except Exception as e:
        print(f"Erro durante o teste: {e}")
        sys.exit(1)