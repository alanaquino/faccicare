from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('generar/', views.generacion_view, name='generacion'),
    path('generar/', views.generacion_view, name='generar'),
    path('vista-previa/', views.vista_previa_reporte, name='vista_previa'),
    path('enviar-correo/', views.enviar_reporte_correo, name='enviar_correo'),
    path('penci/', views.penci_view, name='penci'),
]
