from django.urls import path
from django.contrib.auth import views as auth_views


from olt import views

app_name = 'olt'

urlpatterns = [
    path('', views.home, name="home"),
    path('critical', views.critical_users_list, name='critical_users_list'),
    path('update_users', views.update_users, name='update_users'),
    path('update_onus_all/', views.update_onus_all, name='update_onus_all'),
    path('get_duplicated/', views.get_duplicated, name='get_duplicated'),
    path('details/<int:slot>/<int:port>', views.get_itens_to_port, name='details'),
    path('remover/<int:porta>/', views.remover_ont, name='remover'),
    path('update_values/<int:slot>/<int:port>/', views.update_values, name='update_values'),
    path('delete/<int:slot>/<int:port>/<int:position>/', views.delete, name='delete'),
    path('search/', views.search_view, name='search_view'),
    path('search_ixc/', views.search_ixc, name='search_ixc'),
    path('listar_clientes/', views.listar_clientes, name='listar_clientes'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('accounts/register/', views.register, name='register'),
    path('mikrotik_info/', views.mikrotik_info, name='mikrotik_info'),  # Nova URL para a view mikrotik_info
    # path('enable_nats/', views.enable_nats, name='enable_nats'),
    # path('disable_nats/', views.disable_nats, name='disable_nats'),


]