from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import PacienteViewSet

router = DefaultRouter()
router.register('pacientes', PacienteViewSet, basename='pacientes-api')

urlpatterns = [
    path('', include(router.urls)),
]
