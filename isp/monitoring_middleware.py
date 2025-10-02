import time
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from datetime import datetime, timedelta

# Configurar loggers específicos
api_logger = logging.getLogger('olt.api_access')
security_logger = logging.getLogger('olt.security')
performance_logger = logging.getLogger('olt.performance')
user_activity_logger = logging.getLogger('olt.user_activity')


class MonitoringMiddleware(MiddlewareMixin):
    """
    Middleware para monitoramento de APIs, performance e segurança
    """
    
    def process_request(self, request):
        """Processar início da requisição"""
        request.start_time = time.time()
        request.monitoring_data = {
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET),
        }
        return None
    
    def process_response(self, request, response):
        """Processar fim da requisição"""
        if not hasattr(request, 'start_time'):
            return response
        
        # Calcular tempo de resposta
        response_time = time.time() - request.start_time
        
        # Obter informações do usuário
        user_info = self.get_user_info(request)
        
        # Resolver view name
        try:
            resolver_match = resolve(request.path)
            view_name = f"{resolver_match.app_name}:{resolver_match.url_name}" if resolver_match.app_name else resolver_match.url_name
        except:
            view_name = "unknown"
        
        # Dados completos do monitoramento
        monitoring_data = {
            **request.monitoring_data,
            'response_time': round(response_time * 1000, 2),  # em milissegundos
            'status_code': response.status_code,
            'content_length': len(response.content) if hasattr(response, 'content') else 0,
            'user': user_info,
            'view_name': view_name,
            'timestamp': time.time(),
        }
        
        # Rastrear atividade do usuário
        self.track_user_activity(monitoring_data)
        
        # Log de acesso à API
        if request.path.startswith('/api/'):
            self.log_api_access(monitoring_data)
        
        # Log de performance para requisições lentas
        if response_time > 1.0:  # > 1 segundo
            self.log_slow_request(monitoring_data)
        
        # Log de segurança para tentativas suspeitas
        if self.is_suspicious_request(monitoring_data):
            self.log_security_event(monitoring_data)
        
        return response
    
    def track_user_activity(self, data):
        """Rastrear atividade do usuário para métricas"""
        user_id = data['user'].get('id') or 'anonymous'
        username = data['user'].get('username', 'anonymous')
        
        # Chave única para o usuário
        cache_key = f"user_activity:{user_id}"
        
        # Obter dados existentes do cache
        user_data = cache.get(cache_key, {
            'user_id': user_id,
            'username': username,
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'request_count': 0,
            'endpoints': set(),
            'ip_addresses': set(),
            'status_codes': [],
            'avg_response_time': 0,
            'total_response_time': 0
        })
        
        # Atualizar dados
        user_data['last_seen'] = datetime.now().isoformat()
        user_data['request_count'] += 1
        user_data['endpoints'].add(data['path'])
        user_data['ip_addresses'].add(data['ip_address'])
        user_data['status_codes'].append(data['status_code'])
        user_data['total_response_time'] += data['response_time']
        user_data['avg_response_time'] = user_data['total_response_time'] / user_data['request_count']
        
        # Converter sets para listas para serialização
        if isinstance(user_data['endpoints'], set):
            user_data['endpoints'] = list(user_data['endpoints'])
        if isinstance(user_data['ip_addresses'], set):
            user_data['ip_addresses'] = list(user_data['ip_addresses'])
        
        # Manter apenas os últimos 100 status codes
        if len(user_data['status_codes']) > 100:
            user_data['status_codes'] = user_data['status_codes'][-100:]
        
        # Salvar no cache por 1 hora
        cache.set(cache_key, user_data, 3600)
        
        # Log de atividade do usuário para APIs
        if data['path'].startswith('/api/'):
            user_activity_logger.info(
                f"USER_ACTIVITY: user={username} "
                f"user_id={user_id} "
                f"endpoint={data['path']} "
                f"method={data['method']} "
                f"status={data['status_code']} "
                f"response_time={data['response_time']}ms "
                f"ip={data['ip_address']} "
                f"total_requests={user_data['request_count']}"
            )


class MonitoringMiddleware(MiddlewareMixin):
    """
    Middleware para monitoramento de APIs, performance e segurança
    """
    
    def process_request(self, request):
        """Processar início da requisição"""
        request.start_time = time.time()
        request.monitoring_data = {
            'ip_address': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET),
        }
        return None
    
    def process_response(self, request, response):
        """Processar fim da requisição"""
        if not hasattr(request, 'start_time'):
            return response
        
        # Calcular tempo de resposta
        response_time = time.time() - request.start_time
        
        # Obter informações do usuário
        user_info = self.get_user_info(request)
        
        # Resolver view name
        try:
            resolver_match = resolve(request.path)
            view_name = f"{resolver_match.app_name}:{resolver_match.url_name}" if resolver_match.app_name else resolver_match.url_name
        except:
            view_name = "unknown"
        
        # Dados completos do monitoramento
        monitoring_data = {
            **request.monitoring_data,
            'response_time': round(response_time * 1000, 2),  # em milissegundos
            'status_code': response.status_code,
            'content_length': len(response.content) if hasattr(response, 'content') else 0,
            'user': user_info,
            'view_name': view_name,
            'timestamp': time.time(),
        }
        
        # Log de acesso à API
        if request.path.startswith('/api/'):
            self.log_api_access(monitoring_data)
        
        # Log de performance para requisições lentas
        if response_time > 1.0:  # > 1 segundo
            self.log_slow_request(monitoring_data)
        
        # Log de segurança para tentativas suspeitas
        if self.is_suspicious_request(monitoring_data):
            self.log_security_event(monitoring_data)
        
        return response
    
    def get_client_ip(self, request):
        """Obter IP real do cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_user_info(self, request):
        """Obter informações do usuário"""
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            return {
                'id': request.user.id,
                'username': request.user.username,
                'is_staff': request.user.is_staff,
                'is_authenticated': True
            }
        return {
            'is_authenticated': False,
            'username': 'anonymous'
        }
    
    def log_api_access(self, data):
        """Log específico para acessos à API"""
        message = (
            f"USER:{data['user']['username']} "
            f"IP:{data['ip_address']} "
            f"{data['method']} {data['path']} "
            f"STATUS:{data['status_code']} "
            f"TIME:{data['response_time']}ms"
        )
        
        if data['query_params']:
            message += f" PARAMS:{str(data['query_params'])}"
        
        api_logger.info(message)
    
    def log_slow_request(self, data):
        """Log para requisições lentas"""
        message = (
            f"SLOW_REQUEST: {data['method']} {data['path']} "
            f"TIME:{data['response_time']}ms "
            f"STATUS:{data['status_code']} "
            f"USER:{data['user']['username']} "
            f"IP:{data['ip_address']} "
            f"VIEW:{data['view_name']}"
        )
        
        performance_logger.warning(message)
    
    def is_suspicious_request(self, data):
        """Detectar requisições suspeitas"""
        suspicious_patterns = [
            # Status codes suspeitos
            data['status_code'] in [401, 403, 404, 429],
            # User agents suspeitos
            any(pattern in data['user_agent'].lower() for pattern in ['bot', 'crawler', 'scanner', 'hack']),
            # Paths suspeitos
            any(pattern in data['path'].lower() for pattern in ['.php', '.asp', 'admin', 'wp-', 'phpmyadmin']),
            # Muitos parâmetros (possível injeção)
            len(data['query_params']) > 10,
        ]
        
        return any(suspicious_patterns)
    
    def log_security_event(self, data):
        """Log de eventos de segurança"""
        message = (
            f"SECURITY_EVENT: {data['method']} {data['path']} "
            f"STATUS:{data['status_code']} "
            f"IP:{data['ip_address']} "
            f"USER_AGENT:{data['user_agent'][:100]} "
            f"USER:{data['user']['username']}"
        )
        
        if data['query_params']:
            message += f" PARAMS:{str(data['query_params'])}"
        
        security_logger.warning(message)


class MetricsCollectionMiddleware(MiddlewareMixin):
    """
    Middleware adicional para coleta de métricas agregadas
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Inicializar contadores em memória (em produção usar Redis)
        self.metrics = {
            'request_count': 0,
            'error_count': 0,
            'api_calls': 0,
            'response_times': [],
            'active_users': set(),
            'user_requests': {}
        }
    
    def __call__(self, request):
        # Incrementar contador de requisições
        self.metrics['request_count'] += 1
        
        # Rastrear usuários ativos
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            user_key = f"{request.user.id}:{request.user.username}"
            self.metrics['active_users'].add(user_key)
            
            # Contar requisições por usuário
            if user_key not in self.metrics['user_requests']:
                self.metrics['user_requests'][user_key] = 0
            self.metrics['user_requests'][user_key] += 1
        
        if request.path.startswith('/api/'):
            self.metrics['api_calls'] += 1
        
        start_time = time.time()
        response = self.get_response(request)
        response_time = time.time() - start_time
        
        # Coletar métricas de resposta
        self.metrics['response_times'].append(response_time)
        
        # Manter apenas os últimos 1000 tempos de resposta
        if len(self.metrics['response_times']) > 1000:
            self.metrics['response_times'] = self.metrics['response_times'][-1000:]
        
        # Contar erros
        if response.status_code >= 400:
            self.metrics['error_count'] += 1
        
        return response