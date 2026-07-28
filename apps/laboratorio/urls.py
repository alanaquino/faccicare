from django.urls import path

from . import views

app_name = 'laboratorio'

urlpatterns = [
    path('', views.lista_view, name='lista'),
    path('examenes/', views.lista_view, name='examenes'),
    path('catalogo/parametros/', views.catalogo_parametros_view, name='catalogo_parametros'),
    path('catalogo/parametro/<uuid:pk>/', views.catalogo_parametro_view, name='catalogo_parametro'),
    path('nuevo/', views.crear_view, name='crear'),
    path('nuevo/<str:paciente_pk>/', views.crear_view, name='crear_para_paciente'),
    path('<str:pk>/revisar/', views.marcar_revisado_view, name='marcar_revisado'),
    path('<str:pk>/', views.detalle_view, name='detalle'),
]
