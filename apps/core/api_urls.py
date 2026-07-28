from django.urls import path

from .api_views import CoreAPIView, centros_salud_mapa_view, geocodificar_centro_salud_view

urlpatterns = [
    path('centros-salud/mapa/', centros_salud_mapa_view, name='api-centros-salud-mapa'),
    path('centros-salud/<int:pk>/geocodificar/', geocodificar_centro_salud_view, name='api-centros-salud-geocodificar'),
    path('', CoreAPIView.as_view(), name='api-core'),
]
