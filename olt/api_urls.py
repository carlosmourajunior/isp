from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import api_views, cto_views, health_views, ixc_caixas_views, ixc_correcoes_views, onu_atualizar_views, sinal_views, user_activity_views, vistoria_views

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
    
    # OLTs (cadastro multi-OLT)
    path('olts/', api_views.OltListCreateAPIView.as_view(), name='olt_list_create'),
    path('olts/<int:pk>/', api_views.OltDetailAPIView.as_view(), name='olt_detail'),

    # ONUs
    path('onus/', api_views.ONUListAPIView.as_view(), name='onu_list'),
    path('onus/<int:pk>/', api_views.ONUDetailAPIView.as_view(), name='onu_detail'),
    path('onus/stats/', api_views.onu_stats, name='onu_stats'),
    # Atualização de uma ONU só, da OLT ou do IXC (olt/onu_atualizar_views.py)
    path('onus/<int:pk>/atualizar/', onu_atualizar_views.onu_atualizar, name='onu_atualizar'),
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
    path('olt/system-summary/', api_views.olt_system_summary, name='olt_system_summary'),
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

    # CTOs - inferência de ocupação (olt/cto_views.py)
    path('ctos/', cto_views.cto_list, name='cto_list'),
    # Caixas do projeto que não estão no IXC (olt/ixc_caixas_views.py)
    path('ctos/fora-do-ixc/', ixc_caixas_views.fora_do_ixc, name='ctos_fora_do_ixc'),
    path('ctos/fora-do-ixc/cadastrar/', ixc_caixas_views.fora_do_ixc_cadastrar, name='ctos_fora_do_ixc_cadastrar'),
    path('ctos/fora-do-ixc/vincular/', ixc_caixas_views.fora_do_ixc_vincular, name='ctos_fora_do_ixc_vincular'),
    path('ctos/<int:pk>/', cto_views.cto_detail, name='cto_detail'),
    path('ctos/<int:pk>/splitters/', cto_views.cto_splitters, name='cto_splitters'),
    path('ctos/<int:pk>/portas-inutilizadas/', cto_views.cto_porta_inutilizada, name='cto_porta_inutilizada'),
    path('ctos/<int:pk>/capacidade/', cto_views.cto_capacidade, name='cto_capacidade'),
    path('ctos/<int:pk>/ficha/', cto_views.cto_ficha, name='cto_ficha'),
    path('cto-inferencias/', cto_views.CtoInferenciaListAPIView.as_view(), name='cto_inferencia_list'),
    path('cto-inferencias/resumo/', cto_views.cto_inferencia_resumo, name='cto_inferencia_resumo'),

    # Correções de CTO no IXC: histórico com reversão e aplicação em lote (olt/ixc_correcoes_views.py)
    path('ixc/correcoes/', ixc_correcoes_views.correcoes_historico, name='ixc_correcoes_historico'),
    path('ixc/correcoes/lote/', ixc_correcoes_views.correcoes_lote, name='ixc_correcoes_lote'),
    path('ixc/correcoes/<int:pk>/reverter/', ixc_correcoes_views.correcao_reverter, name='ixc_correcao_reverter'),

    # Sinal óptico: faixas e variação (olt/sinal_views.py)
    path('sinal/resumo/', sinal_views.sinal_resumo, name='sinal_resumo'),
    path('sinal/variacao/', sinal_views.sinal_variacao, name='sinal_variacao'),
    path('sinal/caixas/', sinal_views.sinal_caixas, name='sinal_caixas'),
    path('sinal/caixas/mapa/', sinal_views.sinal_caixas_mapa, name='sinal_caixas_mapa'),

    # Vistoria de CTO em campo (olt/vistoria_views.py)
    path('vistorias/', vistoria_views.vistoria_list, name='vistoria_list'),
    path('vistorias/clientes/', vistoria_views.vistoria_buscar_cliente, name='vistoria_buscar_cliente'),
    path('vistorias/correcoes/', vistoria_views.vistoria_correcoes, name='vistoria_correcoes'),
    path('vistorias/correcoes/aplicar/', vistoria_views.vistoria_aplicar_correcao, name='vistoria_aplicar_correcao'),
    path('vistorias/correcoes/historico/', vistoria_views.vistoria_historico_correcoes, name='vistoria_historico_correcoes'),
    path('ixc/escrita/', vistoria_views.ixc_escrita_estado, name='ixc_escrita_estado'),
    path('vistorias/<int:pk>/', vistoria_views.vistoria_detail, name='vistoria_detail'),
    path('vistorias/<int:pk>/portas/', vistoria_views.vistoria_porta_salvar, name='vistoria_porta_salvar'),
    path('vistorias/<int:pk>/portas/<int:porta>/', vistoria_views.vistoria_porta_remover, name='vistoria_porta_remover'),
    path('vistorias/<int:pk>/registros/<int:registro_id>/', vistoria_views.vistoria_registro_remover, name='vistoria_registro_remover'),
    path('vistorias/<int:pk>/finalizar/', vistoria_views.vistoria_finalizar, name='vistoria_finalizar'),
    path('vistorias/<int:pk>/eventos/', vistoria_views.vistoria_eventos, name='vistoria_eventos'),

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