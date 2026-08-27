import time
import logging
from django.http import HttpResponse
from django.urls import resolve
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry
from django.db import connection
from django.core.cache import cache
from django.contrib.auth.models import User
import psutil

# Registry personalizado para evitar conflitos
registry = CollectorRegistry()

# Métricas do Django
django_requests_total = Counter(
    'django_requests_total', 
    'Total Django requests', 
    ['method', 'endpoint', 'status'],
    registry=registry
)

django_request_duration = Histogram(
    'django_request_duration_seconds',
    'Django request duration in seconds',
    ['method', 'endpoint'],
    registry=registry
)

django_active_connections = Gauge(
    'django_db_connections_active',
    'Active database connections',
    registry=registry
)

# Métricas de usuários
api_requests_by_user = Counter(
    'api_requests_by_user_total',
    'Total API requests by user',
    ['user_id', 'username', 'endpoint', 'method', 'status'],
    registry=registry
)

active_users_count = Gauge(
    'active_users_total',
    'Number of active users in the last hour',
    registry=registry
)

user_session_duration = Histogram(
    'user_session_duration_seconds',
    'User session duration in seconds',
    ['username'],
    registry=registry
)

api_users_response_time = Histogram(
    'api_users_response_time_seconds',
    'API response time by user',
    ['username', 'endpoint'],
    registry=registry
)

# Métricas de sistema
system_memory_usage = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage',
    registry=registry
)

system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=registry
)

system_disk_usage = Gauge(
    'system_disk_usage_percent',
    'System disk usage percentage',
    registry=registry
)

# Métricas específicas da aplicação
olt_onus_total = Gauge(
    'olt_onus_total',
    'Total number of ONUs',
    ['status'],
    registry=registry
)

olt_temperature_celsius = Gauge(
    'olt_temperature_celsius',
    'OLT temperature in Celsius',
    ['slot', 'sensor'],
    registry=registry
)

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def prometheus_metrics(request):
    """
    Endpoint para métricas do Prometheus
    """
    try:
        # Atualizar métricas de sistema
        update_system_metrics()
        
        # Atualizar métricas específicas da aplicação
        update_application_metrics()
        
        # Atualizar métricas de usuários
        update_user_metrics()
        
        # Gerar métricas no formato Prometheus
        metrics = generate_latest(registry)
        return HttpResponse(metrics, content_type=CONTENT_TYPE_LATEST)
        
    except Exception as e:
        logger.error(f"Erro ao gerar métricas: {str(e)}")
        return HttpResponse("# Error generating metrics\n", content_type=CONTENT_TYPE_LATEST)


def update_user_metrics():
    """Atualizar métricas de usuários ativos"""
    try:
        from datetime import datetime, timedelta
        
        # Obter todas as chaves de atividade de usuário do cache
        cache_keys = []
        if hasattr(cache, '_cache') and hasattr(cache._cache, 'keys'):
            # Para backends que suportam keys()
            try:
                cache_keys = [k for k in cache._cache.keys() if k.startswith('user_activity:')]
            except:
                pass
        
        # Se não conseguir obter as chaves, usar uma abordagem alternativa
        if not cache_keys:
            # Buscar usuários que fizeram login recentemente
            recent_users = User.objects.filter(
                last_login__gte=datetime.now() - timedelta(hours=1)
            ).values_list('id', flat=True)
            
            cache_keys = [f'user_activity:{user_id}' for user_id in recent_users]
        
        active_users = 0
        current_time = datetime.now()
        
        for cache_key in cache_keys:
            user_data = cache.get(cache_key)
            if user_data:
                # Verificar se o usuário esteve ativo na última hora
                try:
                    last_seen = datetime.fromisoformat(user_data['last_seen'])
                    if current_time - last_seen <= timedelta(hours=1):
                        active_users += 1
                except (ValueError, KeyError):
                    continue
        
        # Atualizar métrica de usuários ativos
        active_users_count.set(active_users)
        
    except Exception as e:
        logger.error(f"Erro ao atualizar métricas de usuários: {str(e)}")
        # Definir valor padrão em caso de erro
        active_users_count.set(0)


def update_system_metrics():
    """Atualizar métricas de sistema"""
    try:
        # Memória
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.percent)
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        system_cpu_usage.set(cpu_percent)
        
        # Disco
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        system_disk_usage.set(disk_percent)
        
        # Conexões de banco de dados
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT count(*) 
                FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            active_connections = cursor.fetchone()[0]
            django_active_connections.set(active_connections)
            
    except Exception as e:
        logger.error(f"Erro ao atualizar métricas de sistema: {str(e)}")


def update_application_metrics():
    """Atualizar métricas específicas da aplicação"""
    try:
        from .models import ONU, OltTemperature
        
        # Métricas das ONUs
        onus_online = ONU.objects.filter(oper_state='up').count()
        onus_offline = ONU.objects.filter(oper_state='down').count()
        
        olt_onus_total.labels(status='online').set(onus_online)
        olt_onus_total.labels(status='offline').set(onus_offline)
        
        # Métricas de temperatura da OLT
        temperatures = OltTemperature.objects.all()
        for temp in temperatures:
            olt_temperature_celsius.labels(
                slot=temp.slot_name, 
                sensor=temp.sensor_id
            ).set(temp.actual_temp or 0)
            
    except Exception as e:
        logger.error(f"Erro ao atualizar métricas da aplicação: {str(e)}")


class PrometheusMiddleware:
    """
    Middleware para coletar métricas do Prometheus
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Calcular duração
        duration = time.time() - start_time
        
        # Obter endpoint
        try:
            resolver_match = resolve(request.path)
            endpoint = f"{resolver_match.app_name}:{resolver_match.url_name}" if resolver_match.app_name else resolver_match.url_name
        except:
            endpoint = request.path
        
        # Registrar métricas gerais
        django_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code
        ).inc()
        
        django_request_duration.labels(
            method=request.method,
            endpoint=endpoint
        ).observe(duration)
        
        # Registrar métricas específicas de usuários para APIs
        if request.path.startswith('/api/') and hasattr(request, 'user'):
            from django.contrib.auth.models import AnonymousUser
            
            if not isinstance(request.user, AnonymousUser):
                # Métricas de requisições por usuário
                api_requests_by_user.labels(
                    user_id=str(request.user.id),
                    username=request.user.username,
                    endpoint=endpoint,
                    method=request.method,
                    status=str(response.status_code)
                ).inc()
                
                # Métricas de tempo de resposta por usuário
                api_users_response_time.labels(
                    username=request.user.username,
                    endpoint=endpoint
                ).observe(duration)
        
        return response