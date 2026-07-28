from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('notificaciones/', views.notificaciones_view, name='notificaciones'),
    path('notificaciones/marcar-leida/<uuid:pk>/', views.marcar_leida_view, name='marcar_leida'),
    path('notificaciones/marcar-no-leida/<uuid:pk>/', views.marcar_no_leida_view, name='marcar_no_leida'),
    path('notificaciones/eliminar/<uuid:pk>/', views.eliminar_notificacion_view, name='eliminar_notificacion'),
    path('notificaciones/marcar-todas-leidas/', views.marcar_todas_leidas_view, name='marcar_todas_leidas'),
    path('notificaciones/abrir/<uuid:pk>/', views.abrir_notificacion_view, name='abrir_notificacion'),
    path('notificaciones/api/', views.notificaciones_api_view, name='notificaciones_api'),
]
