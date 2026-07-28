"""
FACCI Care — Middleware personalizado para seguridad y auditoría de peticiones médicas.
"""
import logging
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from .audit import reset_current_request, set_current_request

logger = logging.getLogger(__name__)


class LoginRequiredMiddleware:
    """Protege vistas web internas sin interferir con admin, API ni assets."""

    rutas_publicas = (
        '/login/',
        '/logout/',
        '/acceso/',
        '/admin/',
        '/api/',
        '/api-auth/',
        '/static/',
        '/media/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_current_request(request)
        try:
            path = request.path
            if not request.user.is_authenticated and not path.startswith(self.rutas_publicas):
                return redirect(f'{settings.LOGIN_URL}?next={path}')
            return self.get_response(request)
        finally:
            reset_current_request(token)


class ControlAccesoPorRolMiddleware:
    """
    Restringe el acceso según el rol del usuario autenticado.
    - PADRE_TUTOR solo puede acceder al portal de padres (/padres/).
    - Roles de personal no pueden acceder al portal de padres (/padres/).
    """

    rutas_padre_permitidas = (
        '/padres/',
        '/recursos/',
        '/login/',
        '/logout/',
        '/acceso/',
        '/static/',
        '/media/',
        '/notificaciones/',
        # API de notificaciones usada por el navbar del portal de padres
        '/mensajes/notificaciones/',
        '/mensajes/notificaciones/api/',
        '/mensajes/notificaciones/marcar-leida/',
        '/mensajes/notificaciones/eliminar/',
        '/mensajes/notificaciones/marcar-todas-leidas/',
    )

    rutas_personal_prohibidas = (
        '/padres/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        rol = getattr(request.user, 'rol', None)
        path = request.path

        if rol == 'PADRE_TUTOR':
            if not path.startswith(self.rutas_padre_permitidas):
                return redirect(reverse('padres:estado'))

        elif rol in ('ADMIN', 'MEDICO', 'PEDIATRA', 'ONCOLOGO', 'PERSONAL_FACCI', 'TRABAJADORA_SOCIAL', 'ENFERMERA'):
            if path.startswith('/padres/'):
                return redirect(reverse('home'))

        return self.get_response(request)


class AuditarAccesoMiddleware:
    """Registra los accesos de usuarios a historias clínicas y datos de pacientes."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Procesar petición
        response = self.get_response(request)

        # Registrar accesos a rutas críticas de pacientes
        if "pacientes" in request.path:
            # En producción: registraría en la base de datos de auditoría
            logger.info(f"Acceso registrado: Path {request.path} por IP {request.META.get('REMOTE_ADDR')}")

        return response
