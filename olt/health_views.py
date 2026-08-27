import time
import json
import logging
import psutil
from django.http import JsonResponse
from django.db import connection, connections
from django.core.cache import cache
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import redis
from django.utils import timezone

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check básico - sempre retorna 200 se a aplicação estiver rodando
    """
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'ISP OLT Management API'
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_detailed(request):
    """
    Health check detalhado com verificação de dependências
    """
    start_time = time.time()
    health_data = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'ISP OLT Management API',
        'version': '1.0.0',
        'checks': {}
    }
    
    overall_healthy = True
    
    # 1. Verificar banco de dados
    db_healthy, db_info = check_database()
    health_data['checks']['database'] = db_info
    if not db_healthy:
        overall_healthy = False
    
    # 2. Verificar Redis
    redis_healthy, redis_info = check_redis()
    health_data['checks']['redis'] = redis_info
    if not redis_healthy:
        overall_healthy = False
    
    # 3. Verificar sistema de arquivos
    disk_healthy, disk_info = check_disk_space()
    health_data['checks']['disk'] = disk_info
    if not disk_healthy:
        overall_healthy = False
    
    # 4. Verificar memória
    memory_healthy, memory_info = check_memory()
    health_data['checks']['memory'] = memory_info
    if not memory_healthy:
        overall_healthy = False
    
    # 5. Verificar CPU
    cpu_info = check_cpu()
    health_data['checks']['cpu'] = cpu_info
    
    # Tempo total do health check
    health_data['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
    
    # Status geral
    if not overall_healthy:
        health_data['status'] = 'unhealthy'
        return Response(health_data, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    return Response(health_data)


@api_view(['GET'])
@permission_classes([AllowAny])
def metrics(request):
    """
    Endpoint de métricas básicas para monitoramento
    """
    try:
        # Métricas do sistema
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Métricas de conexões de banco
        db_connections = len(connections.all())
        
        # Métricas do Redis (se disponível)
        redis_info = {}
        try:
            r = redis.Redis.from_url('redis://redis:6379/0')
            redis_info = r.info()
        except:
            redis_info = {'status': 'unavailable'}
        
        metrics_data = {
            'timestamp': timezone.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': round(memory.available / 1024 / 1024, 2),
                'disk_percent': round((disk.used / disk.total) * 100, 2),
                'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
            },
            'database': {
                'connections_count': db_connections,
            },
            'redis': {
                'connected_clients': redis_info.get('connected_clients', 'N/A'),
                'used_memory_human': redis_info.get('used_memory_human', 'N/A'),
                'total_commands_processed': redis_info.get('total_commands_processed', 'N/A'),
            }
        }
        
        return Response(metrics_data)
        
    except Exception as e:
        logger.error(f"Erro ao coletar métricas: {str(e)}")
        return Response(
            {'error': 'Erro ao coletar métricas', 'detail': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def check_database():
    """Verificar conexão com banco de dados"""
    try:
        start_time = time.time()
        
        # Testar conexão
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        # Obter informações do banco
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            db_version = cursor.fetchone()[0]
        
        return True, {
            'status': 'healthy',
            'response_time_ms': response_time,
            'version': db_version,
            'connection_params': {
                'host': settings.DATABASES['default']['HOST'],
                'port': settings.DATABASES['default']['PORT'],
                'name': settings.DATABASES['default']['NAME']
            }
        }
        
    except Exception as e:
        return False, {
            'status': 'unhealthy',
            'error': str(e)
        }


def check_redis():
    """Verificar conexão com Redis"""
    try:
        start_time = time.time()
        
        # Testar conexão com Redis
        r = redis.Redis.from_url('redis://redis:6379/0')
        r.ping()
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        # Obter informações do Redis
        info = r.info()
        
        return True, {
            'status': 'healthy',
            'response_time_ms': response_time,
            'version': info.get('redis_version'),
            'connected_clients': info.get('connected_clients'),
            'used_memory': info.get('used_memory_human'),
            'uptime_seconds': info.get('uptime_in_seconds')
        }
        
    except Exception as e:
        return False, {
            'status': 'unhealthy',
            'error': str(e)
        }


def check_disk_space():
    """Verificar espaço em disco"""
    try:
        disk = psutil.disk_usage('/')
        
        free_percent = (disk.free / disk.total) * 100
        used_percent = (disk.used / disk.total) * 100
        
        # Considera crítico se menos de 10% livre
        is_healthy = free_percent > 10
        
        return is_healthy, {
            'status': 'healthy' if is_healthy else 'critical',
            'total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
            'used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
            'free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
            'used_percent': round(used_percent, 2),
            'free_percent': round(free_percent, 2)
        }
        
    except Exception as e:
        return False, {
            'status': 'error',
            'error': str(e)
        }


def check_memory():
    """Verificar uso de memória"""
    try:
        memory = psutil.virtual_memory()
        
        # Considera crítico se mais de 90% usado
        is_healthy = memory.percent < 90
        
        return is_healthy, {
            'status': 'healthy' if is_healthy else 'critical',
            'total_gb': round(memory.total / 1024 / 1024 / 1024, 2),
            'available_gb': round(memory.available / 1024 / 1024 / 1024, 2),
            'used_percent': memory.percent,
            'available_percent': round((memory.available / memory.total) * 100, 2)
        }
        
    except Exception as e:
        return False, {
            'status': 'error',
            'error': str(e)
        }


def check_cpu():
    """Verificar uso de CPU"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        return {
            'status': 'healthy' if cpu_percent < 80 else 'warning',
            'usage_percent': cpu_percent,
            'core_count': cpu_count,
            'load_average': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else 'N/A'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness(request):
    """
    Readiness probe - verifica se a aplicação está pronta para receber tráfego
    """
    try:
        # Verificações críticas para readiness
        checks = []
        
        # 1. Banco de dados deve estar acessível
        db_healthy, _ = check_database()
        checks.append(('database', db_healthy))
        
        # 2. Redis deve estar acessível
        redis_healthy, _ = check_redis()
        checks.append(('redis', redis_healthy))
        
        # Se todas as verificações passaram
        all_healthy = all(healthy for _, healthy in checks)
        
        if all_healthy:
            return Response({
                'status': 'ready',
                'timestamp': timezone.now().isoformat(),
                'checks': {name: 'ok' for name, _ in checks}
            })
        else:
            return Response({
                'status': 'not ready',
                'timestamp': timezone.now().isoformat(),
                'checks': {name: 'ok' if healthy else 'failed' for name, healthy in checks}
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness(request):
    """
    Liveness probe - verifica se a aplicação está viva
    """
    return Response({
        'status': 'alive',
        'timestamp': timezone.now().isoformat()
    })