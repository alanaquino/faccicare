from django.urls import path

from . import api_views

urlpatterns = [
    path('notificaciones/', api_views.NotificacionListView.as_view(), name='api-notificaciones-list'),
    path('notificaciones/conteo/', api_views.conteo_no_leidas, name='api-notificaciones-conteo'),
    path('notificaciones/leer-todas/', api_views.marcar_todas_leidas_api, name='api-notificaciones-leer-todas'),
    path('notificaciones/<uuid:pk>/leer/', api_views.marcar_notificacion_leida_api, name='api-notificacion-leer'),
]
