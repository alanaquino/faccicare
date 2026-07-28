from django.urls import path
from . import views

app_name = 'alojamiento'

urlpatterns = [
    path('', views.lista_view, name='lista'),
    path('nuevo/', views.crear_view, name='crear'),
    path('nuevo/<str:paciente_pk>/', views.crear_view, name='crear_para_paciente'),
    path('habitaciones/', views.habitaciones_view, name='habitaciones'),
    path('habitaciones/<str:pk>/toggle/', views.habitacion_toggle_view, name='habitacion_toggle'),
    path('habitaciones/<str:pk>/eliminar/', views.habitacion_eliminar_view, name='habitacion_eliminar'),
    path('reportes/estancias/', views.reporte_estancias, name='reporte_estancias'),
    path('reportes/estancias/pdf/', views.reporte_estancias_pdf, name='reporte_estancias_pdf'),
    path('estancias/<str:pk>/entrega/', views.entrega_habitacion, name='entrega_habitacion'),
    path('estancias/<str:pk>/entrega/pdf/', views.entrega_habitacion_pdf, name='entrega_habitacion_pdf'),
    path('estancias/<str:pk>/entrega/imprimir/', views.entrega_habitacion_imprimir, name='entrega_habitacion_imprimir'),
    path('estancias/<str:pk>/editar/', views.editar_view, name='editar'),
    path('<str:pk>/checkout/', views.checkout_view, name='checkout'),
    path('<str:pk>/formulario/', views.formulario_estancia, name='formulario_estancia'),
    path('<str:pk>/pdf/', views.formulario_estancia_pdf, name='formulario_estancia_pdf'),
    path('<str:pk>/', views.detalle_view, name='detalle'),
]
