from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import api_views, health_views, prometheus_views, alert_views, user_activity_views

app_name = 'api'

urlpatterns = [
    # Health Checks e Monitoramento
    path('health/', health_views.health_check, name='health_check'),
    path('health/detailed/', health_views.health_detailed, name='health_detailed'),
    path('health/readiness/', health_views.readiness, name='readiness'),
    path('health/liveness/', health_views.liveness, name='liveness'),
    path('metrics/', prometheus_views.prometheus_metrics, name='prometheus_metrics'),
    
    # Alertas
    path('alerts/webhook', alert_views.alertmanager_webhook, name='alertmanager_webhook'),
    path('alerts/status/', alert_views.alert_status, name='alert_status'),
    path('alerts/test/', alert_views.test_alert, name='test_alert'),
    
    # Monitoramento de Usuários (Admin apenas)
    path('monitoring/users/active/', user_activity_views.active_users_list, name='active_users_list'),
    path('monitoring/users/<int:user_id>/activity/', user_activity_views.user_activity_details, name='user_activity_details'),
    path('monitoring/api/usage-stats/', user_activity_views.api_usage_stats, name='api_usage_stats'),
    
    # Autenticação JWT
    path('auth/login/', api_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # ONUs
    path('onus/', api_views.ONUListAPIView.as_view(), name='onu_list'),
    path('onus/<int:pk>/', api_views.ONUDetailAPIView.as_view(), name='onu_detail'),
    path('onus/stats/', api_views.onu_stats, name='onu_stats'),
    path('onus/pon/<str:pon>/', api_views.onu_by_pon, name='onu_by_pon'),
    path('onus/search/', api_views.onu_search, name='onu_search'),
    
    # Portas OLT
    path('olt-users/', api_views.OltUsersListAPIView.as_view(), name='olt_users_list'),
    
    # Clientes Fibra
    path('clientes-fibra/', api_views.ClienteFibraListAPIView.as_view(), name='clientes_fibra_list'),
    
    # Sistema OLT
    path('olt/system-info/', api_views.OltSystemInfoAPIView.as_view(), name='olt_system_info'),
    path('olt/slots/', api_views.OltSlotListAPIView.as_view(), name='olt_slots'),
    path('olt/temperatures/', api_views.OltTemperatureListAPIView.as_view(), name='olt_temperatures'),
    path('olt/sfp-diagnostics/', api_views.OltSfpDiagnosticsListAPIView.as_view(), name='olt_sfp_diagnostics'),
    path('olt/system-stats/', api_views.olt_system_stats, name='olt_system_stats'),
    path('olt/temperature-alerts/', api_views.olt_temperature_alerts, name='olt_temperature_alerts'),
    path('olt/update-system-data/', api_views.update_olt_system_data, name='update_olt_system_data'),
]