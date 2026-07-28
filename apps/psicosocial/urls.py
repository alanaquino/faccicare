from django.urls import path

from . import views

app_name = 'psicosocial'

urlpatterns = [
    path('', views.lista_view, name='lista'),
    path('nuevo/', views.crear_view, name='crear'),
    path('nuevo/<str:paciente_pk>/', views.crear_view, name='crear_para_paciente'),
    path('<str:pk>/', views.detalle_view, name='detalle'),
]
