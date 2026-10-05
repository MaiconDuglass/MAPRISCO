"""
URL configuration for maprisco project.

This file defines the main URL patterns for the entire Django project.
It routes incoming requests to the appropriate views or included URLconfs.

For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,    # View for obtaining JWT access and refresh tokens
    TokenRefreshView,       # View for refreshing JWT access tokens
)

# Import ViewSets from project apps
from apps.monitoramento.views import AreaRiscoViewSet, RegistroMonitoramentoViewSet, AlertaViewSet

# Create API router for REST endpoints
router = DefaultRouter()
router.register(r'areas', AreaRiscoViewSet)           # CRUD for risk areas
router.register(r'monitoramento', RegistroMonitoramentoViewSet)  # CRUD for monitoring records
router.register(r'alertas', AlertaViewSet)           # CRUD for alerts

# Main URL patterns for the project
urlpatterns = [
    path('admin/', admin.site.urls),                        # Django admin site
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # JWT token endpoint
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # JWT refresh endpoint
    path('api/', include(router.urls)),                       # REST API endpoints
    path('', include('apps.core.urls')),                      # Core app URLs (web interface)
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)