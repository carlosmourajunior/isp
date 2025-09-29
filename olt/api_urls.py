from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import api_views

app_name = 'api'

urlpatterns = [
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
]