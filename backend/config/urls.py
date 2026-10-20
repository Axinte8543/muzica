
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from . import observability

urlpatterns = [
    path('', RedirectView.as_view(url='http://127.0.0.1:5173/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/users/', include('users.api_urls')),
    path('api/', include('music.urls')),
    path('health/', observability.health, name='health'),
    path('metrics/', observability.metrics, name='metrics'),
]
