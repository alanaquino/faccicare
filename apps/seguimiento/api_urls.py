from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import AlertaClinicaViewSet, ReferenciaMedicaViewSet, SeguimientoPacienteViewSet

router = DefaultRouter()
router.register('referencias', ReferenciaMedicaViewSet, basename='referencias-api')
router.register('seguimientos', SeguimientoPacienteViewSet, basename='seguimientos-api')
router.register('alertas', AlertaClinicaViewSet, basename='alertas-api')

urlpatterns = [
    path('', include(router.urls)),
]
