# nexus_api/urls.py
from django.urls import path
from configurations.views import NexusComponentsView, fetch_secret, remove_secret_key, store_secret
urlpatterns = [
    path('components/', NexusComponentsView.as_view(), name='get_nexus_components'),
    path('store_secret/', store_secret, name='store_secret'),
    path('fetch_secret/', fetch_secret, name='fetch_secret'),
    path('fetch_secret/<str:path>/', fetch_secret, name='fetch_secret'),
    path('remove_secret/', remove_secret_key, name='remove-secret-key'),

]
