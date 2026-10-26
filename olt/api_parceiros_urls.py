"""
Endpoints que entram na documentação pública (/api/docs/, /api/redoc/, /api/schema/).

É só a lista do que mostrar: as rotas de verdade continuam em olt/api_urls.py. Para
liberar um endpoint novo aos parceiros, inclua aqui (mesma view, mesmo caminho) e
documente em olt/api_docs.py.
"""
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from . import api_docs, api_views  # noqa: F401  (api_docs aplica as anotações)

_parceiros = [
    path('auth/login/', api_views.CustomTokenObtainPairView.as_view()),
    path('auth/refresh/', TokenRefreshView.as_view()),
    path('onus/', api_views.ONUListAPIView.as_view()),
    path('onus/<int:pk>/', api_views.ONUDetailAPIView.as_view()),
    path('onus/stats/', api_views.onu_stats),
    path('onus/pon/<str:pon>/', api_views.onu_by_pon),
    path('onus/search/', api_views.onu_search),
    path('olt-users/', api_views.OltUsersListAPIView.as_view()),
    path('clientes-fibra/', api_views.ClienteFibraListAPIView.as_view()),
    path('olt/system-info/', api_views.OltSystemInfoAPIView.as_view()),
    path('olt/slots/', api_views.OltSlotListAPIView.as_view()),
    path('olt/temperatures/', api_views.OltTemperatureListAPIView.as_view()),
    path('olt/sfp-diagnostics/', api_views.OltSfpDiagnosticsListAPIView.as_view()),
    path('olt/system-stats/', api_views.olt_system_stats),
    path('olt/temperature-alerts/', api_views.olt_temperature_alerts),
]

urlpatterns = [path('api/', include(_parceiros))]
