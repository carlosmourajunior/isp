from django.urls import path
from django.contrib.auth import views as auth_views
from olt import views

app_name = 'olt'

urlpatterns = [
    path('', views.home, name="home"),
    path('critical/', views.critical_users_list, name='critical_users_list'),
    path('update_users/', views.update_users, name='update_users'),
    path('update_onus_all/', views.update_onus_all, name='update_onus_all'),
    path('get_duplicated/', views.get_duplicated, name='get_duplicated'),
    path('details/<int:slot>/<int:port>/', views.get_itens_to_port, name='get_itens_to_port'),  # Updated name
    path('remover/<int:porta>/', views.remover_ont, name='remover'),
    path('update_values/<int:port>/<int:slot>/', views.update_values, name='update_values'),
    path('delete/<int:slot>/<int:port>/<int:position>/', views.delete, name='delete'),
    path('reset/<int:slot>/<int:port>/<int:position>/', views.reset_onu, name='reset_onu'),  # Add reset_onu URL pattern
    path('search/', views.search_view, name='search_view'),
    path('search_ixc/', views.search_ixc, name='search_ixc'),
    path('listar_clientes/', views.listar_clientes, name='listar_clientes'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('accounts/register/', views.register, name='register'),
    path('mikrotik_info/', views.mikrotik_info, name='mikrotik_info'),
    path('update-mac/', views.update_mac_values, name='update_mac'),
    path('tasks/', views.view_tasks, name='view_tasks'),
    path('update-all-data/', views.update_all_data, name='update_all_data'),
    path('onus-sem-mac/', views.list_onus_without_mac, name='list_onus_without_mac'),
    path('onus-sem-cliente/', views.list_onus_without_client, name='list_onus_without_client'),
    path('onus/', views.list_onus, name='list_onus'),
    path('onus-oper-state-down/', views.list_onus_with_oper_state_down, name='list_onus_with_oper_state_down'),  # Add URL pattern for ONUs with oper_state 'down'
    path('clients-signal-below-27/', views.list_onus_signal_between_27_and_29, name='clients_signal_below_27'),
    path('clients-signal-below-29/', views.clients_signal_below_29, name='clients_signal_below_29'),
    path('ftth-boxes/', views.list_ftth_boxes_by_occupancy, name='list_ftth_boxes_by_occupancy'),
]