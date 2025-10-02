from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def active_users_list(request):
    """
    Retorna lista de usuários que fizeram requisições recentemente
    Requer permissões de administrador
    """
    try:
        time_window = request.GET.get('hours', 1)
        try:
            time_window = int(time_window)
        except ValueError:
            time_window = 1
        
        cutoff_time = datetime.now() - timedelta(hours=time_window)
        active_users = []
        
        # Tentar obter usuários do cache de atividade
        try:
            # Para sistemas que suportam pattern matching no cache
            if hasattr(cache, 'keys'):
                cache_keys = [k for k in cache.keys('user_activity:*')]
            else:
                # Fallback: buscar usuários que fizeram login recentemente
                recent_user_ids = User.objects.filter(
                    last_login__gte=cutoff_time
                ).values_list('id', flat=True)
                cache_keys = [f'user_activity:{user_id}' for user_id in recent_user_ids]
        
        except Exception:
            # Se falhar, usar abordagem alternativa
            recent_user_ids = User.objects.filter(
                last_login__gte=cutoff_time
            ).values_list('id', flat=True)
            cache_keys = [f'user_activity:{user_id}' for user_id in recent_user_ids]
        
        for cache_key in cache_keys:
            user_data = cache.get(cache_key)
            if user_data:
                try:
                    last_seen = datetime.fromisoformat(user_data['last_seen'])
                    if last_seen >= cutoff_time:
                        active_users.append({
                            'user_id': user_data.get('user_id'),
                            'username': user_data.get('username', 'unknown'),
                            'last_seen': user_data.get('last_seen'),
                            'first_seen': user_data.get('first_seen'),
                            'request_count': user_data.get('request_count', 0),
                            'unique_endpoints': len(user_data.get('endpoints', [])),
                            'endpoints': user_data.get('endpoints', []),
                            'ip_addresses': user_data.get('ip_addresses', []),
                            'avg_response_time': round(user_data.get('avg_response_time', 0), 2),
                            'hours_active': time_window
                        })
                except (ValueError, KeyError) as e:
                    logger.warning(f"Erro ao processar dados do usuário {cache_key}: {e}")
                    continue
        
        # Ordenar por última atividade
        active_users.sort(key=lambda x: x['last_seen'], reverse=True)
        
        return Response({
            'active_users': active_users,
            'total_active_users': len(active_users),
            'time_window_hours': time_window,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter usuários ativos: {str(e)}")
        return Response({
            'error': 'Erro interno do servidor',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def user_activity_details(request, user_id):
    """
    Retorna detalhes de atividade de um usuário específico
    """
    try:
        cache_key = f"user_activity:{user_id}"
        user_data = cache.get(cache_key)
        
        if not user_data:
            return Response({
                'error': 'Usuário não encontrado ou sem atividade recente'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Buscar informações adicionais do usuário
        try:
            user = User.objects.get(id=user_id)
            user_info = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
        except User.DoesNotExist:
            user_info = {
                'id': user_id,
                'username': user_data.get('username', 'unknown'),
                'note': 'Usuário não encontrado no banco de dados'
            }
        
        # Calcular estatísticas adicionais
        status_codes = user_data.get('status_codes', [])
        success_rate = 0
        if status_codes:
            success_count = sum(1 for code in status_codes if 200 <= code < 300)
            success_rate = (success_count / len(status_codes)) * 100
        
        activity_details = {
            'user_info': user_info,
            'activity_summary': {
                'first_seen': user_data.get('first_seen'),
                'last_seen': user_data.get('last_seen'),
                'total_requests': user_data.get('request_count', 0),
                'unique_endpoints': len(user_data.get('endpoints', [])),
                'unique_ip_addresses': len(user_data.get('ip_addresses', [])),
                'avg_response_time': round(user_data.get('avg_response_time', 0), 2),
                'success_rate': round(success_rate, 2)
            },
            'endpoints_accessed': user_data.get('endpoints', []),
            'ip_addresses_used': user_data.get('ip_addresses', []),
            'recent_status_codes': status_codes[-20:] if status_codes else []  # Últimos 20
        }
        
        return Response(activity_details)
        
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do usuário {user_id}: {str(e)}")
        return Response({
            'error': 'Erro interno do servidor',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def api_usage_stats(request):
    """
    Retorna estatísticas gerais de uso da API
    """
    try:
        # Buscar todos os usuários ativos nas últimas 24 horas
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        stats = {
            'total_requests_24h': 0,
            'unique_users_24h': 0,
            'most_active_users': [],
            'most_accessed_endpoints': {},
            'hourly_distribution': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Coletar dados de todos os usuários ativos
        try:
            if hasattr(cache, 'keys'):
                cache_keys = [k for k in cache.keys('user_activity:*')]
            else:
                recent_user_ids = User.objects.filter(
                    last_login__gte=cutoff_time
                ).values_list('id', flat=True)
                cache_keys = [f'user_activity:{user_id}' for user_id in recent_user_ids]
        except Exception:
            recent_user_ids = User.objects.filter(
                last_login__gte=cutoff_time
            ).values_list('id', flat=True)
            cache_keys = [f'user_activity:{user_id}' for user_id in recent_user_ids]
        
        active_users = []
        
        for cache_key in cache_keys:
            user_data = cache.get(cache_key)
            if user_data:
                try:
                    last_seen = datetime.fromisoformat(user_data['last_seen'])
                    if last_seen >= cutoff_time:
                        active_users.append(user_data)
                        stats['total_requests_24h'] += user_data.get('request_count', 0)
                        
                        # Contar endpoints
                        for endpoint in user_data.get('endpoints', []):
                            if endpoint in stats['most_accessed_endpoints']:
                                stats['most_accessed_endpoints'][endpoint] += 1
                            else:
                                stats['most_accessed_endpoints'][endpoint] = 1
                
                except (ValueError, KeyError):
                    continue
        
        stats['unique_users_24h'] = len(active_users)
        
        # Top 10 usuários mais ativos
        active_users.sort(key=lambda x: x.get('request_count', 0), reverse=True)
        stats['most_active_users'] = [
            {
                'username': user.get('username', 'unknown'),
                'user_id': user.get('user_id'),
                'request_count': user.get('request_count', 0),
                'avg_response_time': round(user.get('avg_response_time', 0), 2)
            }
            for user in active_users[:10]
        ]
        
        # Top 10 endpoints mais acessados
        sorted_endpoints = sorted(
            stats['most_accessed_endpoints'].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        stats['most_accessed_endpoints'] = dict(sorted_endpoints[:10])
        
        return Response(stats)
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de uso: {str(e)}")
        return Response({
            'error': 'Erro interno do servidor',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)