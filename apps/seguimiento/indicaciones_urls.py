from django.urls import path

from . import views


app_name = 'indicaciones'

urlpatterns = [
    path('', views.indicaciones_admin_view, name='lista'),
    path('editar/<uuid:paciente_id>/', views.indicaciones_admin_editar_view, name='editar'),
    path('paciente/<uuid:paciente_id>/', views.indicaciones_paciente_view, name='paciente_indicaciones'),
    path('paciente/<uuid:paciente_id>/descargo/', views.descargo_tratamiento_view, name='descargo_tratamiento'),
    path('paciente/<uuid:paciente_id>/descargo/pdf/', views.descargo_tratamiento_pdf_view, name='descargo_tratamiento_pdf'),
]
