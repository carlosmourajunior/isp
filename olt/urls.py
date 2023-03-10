from django.urls import path

from olt import views

app_name = 'olt'

urlpatterns = [
    path('', views.home, name="home"),
    path('critical', views.critical_users_list, name='critical_users_list'),
    path('update_users', views.update_users, name='update_users'),
    path('update_onus/<int:slot>/<int:port>/', views.update_onus, name='update_onus'),
    path('<int:slot>/<int:port>/', views.removable_users_list, name='removables'),
    path('remover/<int:porta>/', views.remover_ont, name='remover'),
]