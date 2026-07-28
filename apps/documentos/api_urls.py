from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import DocumentoMedicoViewSet, SolicitudDocumentoViewSet

app_name = 'documentos-api'

router = DefaultRouter()
router.register(r'documentos', DocumentoMedicoViewSet, basename='documento')
router.register(r'solicitudes', SolicitudDocumentoViewSet, basename='solicitud')

urlpatterns = [
    path('', include(router.urls)),
]
