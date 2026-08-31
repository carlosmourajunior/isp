from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import api_views, health_views, user_activity_views

app_name = 'api'

urlpatterns = [
    # Health Checks
    path('health/', health_views.health_check, name='health_check'),
    path('health/detailed/', health_views.health_detailed, name='health_detailed'),
    path('health/readiness/', health_views.readiness, name='readiness'),
    path('health/liveness/', health_views.liveness, name='liveness'),

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
    path('clientes-fibra/interno/', api_views.ClienteFibraInternalListAPIView.as_view(), name='clientes_fibra_internal_list'),
    
    # Sistema OLT
    path('olt/system-info/', api_views.OltSystemInfoAPIView.as_view(), name='olt_system_info'),
    path('olt/slots/', api_views.OltSlotListAPIView.as_view(), name='olt_slots'),
    path('olt/temperatures/', api_views.OltTemperatureListAPIView.as_view(), name='olt_temperatures'),
    path('olt/sfp-diagnostics/', api_views.OltSfpDiagnosticsListAPIView.as_view(), name='olt_sfp_diagnostics'),
    path('olt/system-stats/', api_views.olt_system_stats, name='olt_system_stats'),
    path('olt/temperature-alerts/', api_views.olt_temperature_alerts, name='olt_temperature_alerts'),
    path('olt/connection-status/', api_views.olt_connection_status, name='olt_connection_status'),
    
    # ⚠️ ENDPOINTS QUE ACESSAM A OLT DIRETAMENTE (FRONTEND ONLY) ⚠️
    path('olt/update-system-data/', api_views.update_olt_system_data, name='update_olt_system_data'),
    path('olt/onus/<int:slot>/<int:port>/<int:position>/', api_views.remove_onu_view, name='remove_onu'),
    path('olt/onus/<int:slot>/<int:port>/<int:position>/reset/', api_views.reset_onu_view, name='reset_onu'),

    # ONUs - leitura adicional (frontend interno)
    path('onus/duplicated/', api_views.DuplicatedOnuListAPIView.as_view(), name='onu_duplicated_list'),
    path('onus/mac-addresses/', api_views.MacAddressListAPIView.as_view(), name='mac_address_list'),
    path('onus/sem-mac/', api_views.OnuWithoutMacListAPIView.as_view(), name='onu_without_mac_list'),
    path('onus/health-summary/', api_views.onu_health_summary, name='onu_health_summary'),

    # Caixas FTTH
    path('olt/ftth-boxes/', api_views.ftth_boxes_by_occupancy, name='ftth_boxes_by_occupancy'),

    # Tarefas em background (RQ)
    path('tasks/', api_views.task_list, name='task_list'),
    path('tasks/update-ports/', api_views.trigger_update_ports, name='trigger_update_ports'),
    path('tasks/update-onus/', api_views.trigger_update_onus, name='trigger_update_onus'),
    path('tasks/update-mac/', api_views.trigger_update_mac, name='trigger_update_mac'),
    path('tasks/sync-clientes/', api_views.trigger_sync_clientes, name='trigger_sync_clientes'),
    path('tasks/update-all/', api_views.trigger_update_all, name='trigger_update_all'),

    # Scheduler automático
    path('scheduler/status/', api_views.scheduler_status_api, name='scheduler_status_api'),
]