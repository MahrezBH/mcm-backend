from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v0/configurations/', include('configurations.v0.urls')),
    path('api/v0/', include('cloud_providers.v0.urls')),
]
