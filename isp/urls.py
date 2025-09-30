from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('olt.api_urls')),  # API endpoints
    path('django-rq/', include('django_rq.urls')),  # Django RQ admin interface
    path('', include('olt.urls')),  # Main app URLs
]