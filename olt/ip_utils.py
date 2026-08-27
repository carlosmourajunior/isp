"""
Funções de validação e utilitários para IPs
"""
import ipaddress
from django.core.exceptions import ValidationError

def validate_ip_address(ip_str):
    """
    Valida se um IP ou range CIDR é válido
    Retorna True se válido, False caso contrário
    """
    try:
        ipaddress.ip_network(ip_str, strict=False)
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False

def validate_and_add_ip(ip_address, description="", force_active=True):
    """
    Valida e adiciona um IP à lista de permitidos
    Retorna (success, message, ip_object)
    """
    from .models import AllowedIP
    from django.core.cache import cache
    
    # Validar formato
    if not validate_ip_address(ip_address):
        return False, f"❌ Formato de IP inválido: {ip_address}. Use formatos como: 192.168.1.1 ou 192.168.1.0/24", None
    
    try:
        # Verificar se já existe
        existing_ip = AllowedIP.objects.filter(ip_address=ip_address).first()
        
        if existing_ip:
            if existing_ip.is_active:
                return False, f"📌 IP {ip_address} já existe e está ativo", existing_ip
            else:
                # Reativar IP existente
                existing_ip.is_active = True
                if description:
                    existing_ip.description = description
                existing_ip.save()
                
                # Limpar cache
                cache.delete('allowed_ips_cache')
                
                return True, f"🔄 IP {ip_address} reativado com sucesso", existing_ip
        else:
            # Criar novo IP
            new_ip = AllowedIP.objects.create(
                ip_address=ip_address,
                description=description or f"Adicionado via comando",
                is_active=force_active
            )
            
            # Limpar cache
            cache.delete('allowed_ips_cache')
            
            return True, f"✅ IP {ip_address} adicionado com sucesso", new_ip
            
    except Exception as e:
        return False, f"❌ Erro ao adicionar IP {ip_address}: {str(e)}", None

def force_refresh_allowed_ips():
    """
    Força a atualização do cache de IPs permitidos
    Útil após mudanças manuais na base de dados
    """
    from django.core.cache import cache
    from .models import AllowedIP
    
    try:
        # Buscar todos os IPs ativos
        active_ips = list(AllowedIP.objects.filter(is_active=True).values_list('ip_address', flat=True))
        
        # Atualizar cache
        cache.set('allowed_ips_cache', active_ips, timeout=3600)  # 1 hora
        
        return True, f"🔄 Cache atualizado com {len(active_ips)} IPs ativos", active_ips
        
    except Exception as e:
        return False, f"❌ Erro ao atualizar cache: {str(e)}", []