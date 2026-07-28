from django.urls import path

from . import views

app_name = 'cribado'

urlpatterns = [
    path('', views.lista_view, name='lista'),
    path('nuevo/', views.cuestionario_view, name='cuestionario'),
    path('exportar/', views.exportar_csv_view, name='exportar'),
    path('resultado/<uuid:pk>/', views.resultado_view, name='resultado'),
    path('resultado/<uuid:pk>/referencia/', views.crear_referencia_view, name='crear_referencia'),
    path('<uuid:pk>/', views.detalle_view, name='detalle'),
    path('<uuid:pk>/editar/', views.editar_view, name='editar'),
]
