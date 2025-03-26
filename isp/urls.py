from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('olt/', include('olt.urls')),  # Change back to olt/
    path('rq/', include('django_rq.urls')),  # Simplify RQ URL
]