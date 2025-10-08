"""
Middleware e decoradores para controlar acesso direto à OLT
"""
from django.http import JsonResponse
from django.conf import settings
from functools import wraps
import ipaddress


def frontend_only(view_func):
    """
    Decorator que permite acesso apenas via frontend (mesmo servidor/IPs específicos)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # IPs permitidos para acesso direto à OLT (apenas frontend)
        frontend_allowed_ips = [
            '127.0.0.1',        # Localhost
            '::1',              # Localhost IPv6
            '172.16.0.0/12',    # Redes Docker internas
            '192.168.0.0/16',   # Redes privadas locais
        ]
        
        # Obter IP do cliente
        client_ip = get_client_ip(request)
        
        # Verificar se é acesso interno/frontend
        if not is_frontend_access(client_ip, frontend_allowed_ips):
            return JsonResponse({
                'error': 'Acesso negado',
                'message': 'Este endpoint só pode ser acessado via frontend interno',
                'code': 'EXTERNAL_ACCESS_DENIED'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def olt_admin_required(view_func):
    """
    Decorator que requer permissões de administrador da OLT
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Verificar se o usuário tem permissão de admin
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Autenticação requerida',
                'message': 'Login necessário para acessar recursos da OLT',
                'code': 'AUTH_REQUIRED'
            }, status=401)
        
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({
                'error': 'Permissão insuficiente',
                'message': 'Apenas administradores podem executar comandos diretos na OLT',
                'code': 'ADMIN_REQUIRED'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def get_client_ip(request):
    """
    Obtém o IP real do cliente
    """
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
            ip = ip_list.split(',')[0].strip()
            if ip and ip != 'unknown':
                return ip
    
    return request.META.get('REMOTE_ADDR', '')


def is_frontend_access(client_ip, allowed_ips):
    """
    Verifica se o IP é de acesso interno (frontend)
    """
    try:
        client_ip_obj = ipaddress.ip_address(client_ip)
        
        for allowed_ip in allowed_ips:
            try:
                # Tenta como IP individual
                if ipaddress.ip_address(allowed_ip) == client_ip_obj:
                    return True
            except ValueError:
                try:
                    # Tenta como range CIDR
                    if client_ip_obj in ipaddress.ip_network(allowed_ip, strict=False):
                        return True
                except ValueError:
                    continue
    except ValueError:
        return False
    
    return False


class OltSecurityMiddleware:
    """
    Middleware para controle de segurança de acesso à OLT
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs que acessam diretamente a OLT
        self.olt_direct_urls = [
            '/api/olt/update-system-data/',
        ]
    
    def __call__(self, request):
        # Verificar se é uma URL que acessa a OLT diretamente
        if any(request.path.startswith(url) for url in self.olt_direct_urls):
            # Aplicar verificação de segurança
            if not self._is_authorized_olt_access(request):
                return JsonResponse({
                    'error': 'Acesso à OLT negado',
                    'message': 'Comandos diretos na OLT só podem ser executados via frontend autorizado',
                    'client_ip': get_client_ip(request),
                    'code': 'OLT_ACCESS_DENIED'
                }, status=403)
        
        response = self.get_response(request)
        return response
    
    def _is_authorized_olt_access(self, request):
        """
        Verifica se o acesso à OLT é autorizado
        """
        # Verificar autenticação
        if not request.user.is_authenticated:
            return False
        
        # Verificar se é admin
        if not (request.user.is_staff or request.user.is_superuser):
            return False
        
        # Verificar se é acesso interno
        client_ip = get_client_ip(request)
        frontend_ips = [
            '127.0.0.1',
            '::1', 
            '172.16.0.0/12',
            '192.168.0.0/16',
        ]
        
        return is_frontend_access(client_ip, frontend_ips)