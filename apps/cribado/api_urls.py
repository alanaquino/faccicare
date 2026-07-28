from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import CuestionarioCribadoViewSet

router = DefaultRouter()
router.register(r'cribados', CuestionarioCribadoViewSet, basename='cribado')

urlpatterns = [
    path('', include(router.urls)),
]
