from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.dashboard import views as dashboard_views
from apps.notificaciones import views as notificaciones_views
from apps.padres import views as padres_views
from apps.seguimiento import views as seguimiento_views


@login_required
def home_view(request):
    if getattr(request.user, 'rol', None) == 'PADRE_TUTOR':
        return redirect('padres:estado')
    return dashboard_views.dashboard_view(request)


urlpatterns = [
    path('', home_view, name='home'),
    path('', include('apps.auth_app.urls')),
    path('admin/', admin.site.urls),
    path('dashboard/', include('apps.dashboard.urls')),
    path('centros-salud/', dashboard_views.centros_salud_view, name='centros_salud'),
    path('centros-salud/<int:pk>/', dashboard_views.ver_centro_view, name='ver_centro'),
    path('centros-salud/<int:pk>/editar/', dashboard_views.editar_centro_view, name='editar_centro'),
    path('pacientes/', include('apps.pacientes.urls')),
    path('cribado/', include('apps.cribado.urls')),
    path('casos/', include('apps.casos.urls')),
    path('referencias/', include('apps.referencias.urls')),
    path('indicaciones/', include('apps.seguimiento.indicaciones_urls')),
    path('seguimiento/', include('apps.seguimiento.urls')),
    path('seguimientos/', seguimiento_views.lista_view, name='seguimientos'),
    path('alertas/', dashboard_views.alertas_view, name='alertas'),
    path('alertas/<uuid:pk>/revisar/', dashboard_views.revisar_alerta_view, name='alerta_revisar'),
    path('alertas/<uuid:pk>/resolver/', dashboard_views.resolver_alerta_view, name='alerta_resolver'),
    path('alertas/<uuid:pk>/descartar/', dashboard_views.descartar_alerta_view, name='alerta_descartar'),
    path('matrices/', dashboard_views.matrices_view, name='matrices'),
    path('matrices/vista-previa/', dashboard_views.matrices_vista_previa_view, name='matrices_vista_previa'),
    path('matrices/descargar-pdf/', dashboard_views.matrices_descargar_pdf_view, name='matrices_descargar_pdf'),
    path('auditoria/', dashboard_views.auditoria_view, name='auditoria'),
    path('ajustes/', dashboard_views.ajustes_view, name='ajustes'),
    path('documentos/', include('apps.documentos.urls')),
    path('reportes/', include('apps.reportes.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('mensajes/', include('apps.notificaciones.urls')),
    path('notificaciones/', notificaciones_views.notificaciones_view, name='notificaciones'),
    # Portal de padres
    path('padres/', include('apps.padres.urls')),
    path('recursos/', padres_views.recursos_educativos_view, name='recursos_familia'),
    path('recursos/<slug:slug>/', padres_views.detalle_recurso_view, name='recurso_familia_detalle'),
    # Autenticación por token JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/core/', include('apps.core.api_urls')),
    path('api/pacientes/', include('apps.pacientes.api_urls')),
    path('api/cribado/', include('apps.cribado.api_urls')),
    path('api/seguimiento/', include('apps.seguimiento.api_urls')),
    path('api/documentos/', include('apps.documentos.api_urls')),
    path('laboratorio/', include('apps.laboratorio.urls')),
    path('psicosocial/', include('apps.psicosocial.urls')),
    path('alojamiento/', include('apps.alojamiento.urls')),
    path('api-auth/', include('rest_framework.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
