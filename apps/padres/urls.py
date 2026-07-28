from django.urls import path
from . import views

app_name = 'padres'

urlpatterns = [
    path('', views.estado_view, name='estado'),
    path('evolucion/', views.evolucion_view, name='evolucion'),
    path('evolucion/reportar/', views.reportar_sintomas_view, name='reportar_sintomas'),
    path('indicaciones/', views.indicaciones_view, name='indicaciones'),
    path('alertas/', views.alertas_view, name='alertas'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/editar/', views.editar_perfil_view, name='editar_perfil'),
    path('marcar-medicamento/', views.marcar_medicamento_view, name='marcar_medicamento'),
    path('documentos/', views.documentos_view, name='documentos'),
    path('documentos/subir/', views.subir_documento_view, name='subir_documento'),
    path('documentos/subir/<uuid:solicitud_id>/', views.subir_documento_view, name='subir_documento_solicitud'),
    path('documentos/ver/<uuid:doc_id>/', views.ver_documento_view, name='ver_documento'),
    path('recursos/', views.recursos_educativos_view, name='recursos_educativos'),
    path('recursos/<slug:slug>/', views.detalle_recurso_view, name='detalle_recurso'),
]
