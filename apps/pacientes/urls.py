from django.urls import path
from . import views

app_name = 'pacientes'

urlpatterns = [
    path('', views.lista_view, name='lista'),
    path('nuevo/', views.registro_view, name='registro'),
    path('tutor/verificar-cedula/', views.verificar_tutor_cedula, name='verificar_tutor_cedula'),
    path('<uuid:pk>/ficha/', views.ficha_paciente, name='ficha_paciente'),
    path('<uuid:pk>/ficha/pdf/', views.ficha_paciente_pdf, name='ficha_paciente_pdf'),
    path('<uuid:pk>/', views.expediente_view, name='expediente'),
    path('<uuid:pk>/editar/', views.editar_view, name='editar'),
    path('<uuid:pk>/resetear-pin/', views.resetear_pin_padre, name='resetear_pin'),
]
