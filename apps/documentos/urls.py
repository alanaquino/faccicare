from django.urls import path
from . import views

app_name = 'documentos'

urlpatterns = [
    path('', views.lista_view, name='lista'),
    path('subir/', views.subir_view, name='subir'),
    path('<uuid:pk>/', views.detalle_view, name='detalle'),
    path('<uuid:pk>/descargar/', views.descargar_view, name='descargar'),
    path('<uuid:pk>/preview/', views.vista_previa_view, name='preview'),
    path('<uuid:pk>/eliminar/', views.eliminar_view, name='eliminar'),
    path('<uuid:pk>/cambiar-estado/', views.cambiar_estado_view, name='cambiar_estado'),
    path('<uuid:pk>/cambiar-visibilidad/', views.cambiar_visibilidad_view, name='cambiar_visibilidad'),
    path('solicitudes/', views.solicitudes_view, name='solicitudes'),
]
