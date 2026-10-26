from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAdminUser

# Documentação interna (todos os endpoints): só para admin logado no /admin/.
_interno = {'authentication_classes': [SessionAuthentication], 'permission_classes': [IsAdminUser]}

urlpatterns = [
    path('admin/', admin.site.urls),
    # Documentação da API: pública só com os endpoints de parceiros (olt/api_parceiros_urls.py)
    path('api/schema/', SpectacularAPIView.as_view(urlconf='olt.api_parceiros_urls'), name='api_schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='api_schema'), name='api_redoc'),
    path('api/schema/interno/', SpectacularAPIView.as_view(**_interno), name='api_schema_interno'),
    path('api/docs/interno/', SpectacularSwaggerView.as_view(url_name='api_schema_interno', **_interno),
         name='api_docs_interno'),
    path('api/', include('olt.api_urls')),  # API endpoints
    path('django-rq/', include('django_rq.urls')),  # Django RQ admin interface
    path('', include('olt.urls')),  # Main app URLs
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)