"""
Middleware para controle de acesso por IP.
Este middleware verifica se o IP do cliente está na lista de IPs permitidos.
"""
from django.http import HttpResponseForbidden
from django.conf import settings
import ipaddress


class IPWhitelistMiddleware:
    """
    Middleware que restringe o acesso apenas aos IPs listados em ALLOWED_IPS.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Código executado para cada request antes da view ser chamada.
        
        if not self.is_ip_allowed(request):
            return HttpResponseForbidden(
                '<h1>Acesso Negado</h1>'
                '<p>Seu IP não está autorizado a acessar este sistema.</p>'
                '<p>Entre em contato com o administrador se você acredita que isso é um erro.</p>'
            )

        response = self.get_response(request)

        # Código executado para cada request/response após a view ser chamada.

        return response

    def get_client_ip(self, request):
        """
        Obtém o IP real do cliente, considerando proxies e load balancers.
        Em ambiente Docker, é comum ter múltiplos proxies.
        """
        # Lista de headers que podem conter o IP real do cliente
        ip_headers = [
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_X_FORWARDED',
            'HTTP_X_CLUSTER_CLIENT_IP',
            'HTTP_FORWARDED_FOR',
            'HTTP_FORWARDED',
        ]
        
        for header in ip_headers:
            ip_list = request.META.get(header)
            if ip_list:
                # Pega o primeiro IP da lista (IP original do cliente)
                ip = ip_list.split(',')[0].strip()
                if ip and ip != 'unknown':
                    return ip
        
        # Fallback para REMOTE_ADDR
        return request.META.get('REMOTE_ADDR', '')

    def is_ip_allowed(self, request):
        """
        Verifica se o IP do cliente está na lista de IPs permitidos.
        Suporta IPs individuais e ranges (CIDR).
        """
        client_ip = self.get_client_ip(request)
        allowed_ips = getattr(settings, 'ALLOWED_IPS', [])
        
        # Se não há IPs configurados, permite acesso (para evitar lockout)
        if not allowed_ips:
            return True
            
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            
            for allowed_ip in allowed_ips:
                try:
                    # Tenta como um IP individual primeiro
                    if ipaddress.ip_address(allowed_ip) == client_ip_obj:
                        return True
                except ValueError:
                    try:
                        # Tenta como uma rede/range CIDR
                        if client_ip_obj in ipaddress.ip_network(allowed_ip, strict=False):
                            return True
                    except ValueError:
                        # IP inválido na configuração, ignora
                        continue
        except ValueError:
            # IP do cliente inválido, nega acesso
            return False
            
        return False