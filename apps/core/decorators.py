"""
FACCI Care — Decoradores para control de acceso basado en roles.
"""
import logging
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

logger = logging.getLogger('facci.acceso')


def _log_acceso_denegado(request, roles_permitidos=None):
    rol = getattr(request.user, 'rol', '?')
    logger.warning(
        'ACCESO DENEGADO | usuario=%s | rol=%s | path=%s | ip=%s | permitidos=%s',
        request.user.username,
        rol,
        request.path,
        request.META.get('REMOTE_ADDR', '?'),
        ','.join(roles_permitidos) if roles_permitidos else 'N/A',
    )


def roles_requeridos(*roles):
    """Permite acceso solo a los roles listados. Redirige al home si no autorizado."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'{reverse("login")}?next={request.path}')
            if getattr(request.user, 'rol', None) not in roles:
                _log_acceso_denegado(request, roles)
                messages.error(request, 'No tienes permiso para acceder a esta sección.')
                return redirect(reverse('home'))
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def solo_personal(view_func):
    """Bloquea el acceso a PADRE_TUTOR. Redirige a su portal."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{reverse("login")}?next={request.path}')
        if getattr(request.user, 'rol', None) == 'PADRE_TUTOR':
            return redirect(reverse('padres:estado'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def medico_requerido(view_func):
    """Permite acceso solo a médicos y oncólogos."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{reverse("login")}?next={request.path}')
        rol = getattr(request.user, 'rol', None)
        roles_medicos = ('MEDICO', 'PEDIATRA', 'ONCOLOGO', 'ADMIN')
        if rol not in roles_medicos:
            _log_acceso_denegado(request, roles_medicos)
            messages.error(request, 'Esta sección es solo para personal médico.')
            return redirect(reverse('home'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def rol_requerido(roles_permitidos):
    """Decorador genérico para limitar vistas a roles específicos."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'{reverse("login")}?next={request.path}')
            if getattr(request.user, 'rol', None) not in roles_permitidos:
                _log_acceso_denegado(request, list(roles_permitidos))
                messages.error(request, 'No tienes permiso para acceder a esta sección.')
                return redirect(reverse('home'))
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def requiere_acceso(propiedad):
    """Permite acceso si el usuario cumple una propiedad de la matriz (CustomUser).

    Une la vista a la MISMA propiedad que decide la visibilidad en el menú
    (p. ej. 'puede_ver_cribado'), evitando que el menú y el acceso real se
    desincronicen. Redirige al home si la propiedad es falsa.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'{reverse("login")}?next={request.path}')
            if getattr(request.user, 'rol', None) == 'PADRE_TUTOR':
                return redirect(reverse('padres:estado'))
            if getattr(request.user, 'rol', None) != 'ADMIN' and not getattr(request.user, propiedad, False):
                _log_acceso_denegado(request, [propiedad])
                messages.error(request, 'No tienes permiso para acceder a esta sección.')
                return redirect(reverse('home'))
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def staff_facci_requerido(view_func):
    """Permite acceso a Coordinador FACCI, Trabajo Social y Admin."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{reverse("login")}?next={request.path}')
        rol = getattr(request.user, 'rol', None)
        roles_facci = ('PERSONAL_FACCI', 'TRABAJADORA_SOCIAL', 'ADMIN')
        if rol not in roles_facci:
            _log_acceso_denegado(request, roles_facci)
            messages.error(request, 'Esta sección es para el equipo FACCI.')
            return redirect(reverse('home'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def enfermera_requerida(view_func):
    """Permite acceso a Enfermera, médicos clínicos y Admin."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{reverse("login")}?next={request.path}')
        rol = getattr(request.user, 'rol', None)
        roles_enfermeria = ('ENFERMERA', 'MEDICO', 'PEDIATRA', 'ONCOLOGO', 'ADMIN')
        if rol not in roles_enfermeria:
            _log_acceso_denegado(request, roles_enfermeria)
            messages.error(request, 'No tienes permiso para acceder a esta sección.')
            return redirect(reverse('home'))
        return view_func(request, *args, **kwargs)
    return _wrapped_view
