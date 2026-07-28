from django.urls import path
from . import views

app_name = 'referencias'

urlpatterns = [
    path('', views.lista_view, name='lista'),
    path('nueva/', views.crear_view, name='crear'),
    path('paciente/<str:paciente_id>/historial/', views.historial_paciente, name='historial_paciente'),
    path('ingreso-casa-facci/nuevo/', views.crear_ingreso_casa_facci, name='crear_ingreso_casa_facci_nuevo'),
    path('ingreso-casa-facci/<str:pk>/formulario/', views.formulario_ingreso_casa_facci, name='formulario_ingreso_casa_facci'),
    path('ingreso-casa-facci/<str:pk>/pdf/', views.formulario_ingreso_casa_facci_pdf, name='formulario_ingreso_casa_facci_pdf'),
    path('contrarreferencia/<str:pk>/', views.contrarreferencia_detalle_view, name='contrarreferencia_detalle'),
    path('contra/<str:pk>/', views.contrarreferencia_detalle_view, name='contrarreferencia_detalle_legacy'),
    path('<str:pk>/estado/', views.detalle_view, name='actualizar_estado'),
    path('<str:pk>/ingreso-casa-facci/', views.crear_ingreso_casa_facci, name='crear_ingreso_casa_facci'),
    path('<str:ref_pk>/contrarreferir/', views.contrarreferencia_crear_view, name='contrarreferencia_crear'),
    path('<str:ref_pk>/contrarreferir/', views.contrarreferencia_crear_view, name='contrarreferir'),
    path('<str:pk>/guardar-msp/', views.guardar_documento_msp_view, name='guardar_documento_msp'),
    path('<str:pk>/imprimir/', views.imprimir_view, name='imprimir'),
    path('<str:pk>/', views.detalle_view, name='detalle'),

]
