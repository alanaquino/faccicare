from django.urls import path
from . import views

app_name = 'seguimiento'

urlpatterns = [
    path('', views.lista_view, name='lista'),
    path('registrar/', views.registrar_seguimiento_view, name='registrar'),
    path('caso/', views.seguimiento_view, name='seguimiento'),
    path('timeline/', views.timeline_view, name='timeline'),
    path('indicaciones/', views.indicaciones_admin_view, name='indicaciones_admin'),
    path('indicaciones/paciente/<uuid:paciente_id>/', views.indicaciones_paciente_view, name='paciente_indicaciones'),
    path('indicaciones/paciente/<uuid:paciente_id>/descargo/', views.descargo_tratamiento_view, name='descargo_tratamiento'),
    path('indicaciones/paciente/<uuid:paciente_id>/descargo/pdf/', views.descargo_tratamiento_pdf_view, name='descargo_tratamiento_pdf'),
    path('indicaciones/editar/<uuid:paciente_id>/', views.indicaciones_admin_editar_view, name='indicaciones_admin_editar'),
]
