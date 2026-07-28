from contextvars import ContextVar

from django.utils import timezone


_current_request = ContextVar('audit_current_request', default=None)


def set_current_request(request):
    return _current_request.set(request)


def reset_current_request(token):
    _current_request.reset(token)


def get_current_request():
    return _current_request.get()


def get_client_ip(request=None):
    request = request or get_current_request()
    if not request:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def usuario_actual(fallback=None, request=None):
    request = request or get_current_request()
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        return user
    if fallback and getattr(fallback, 'is_authenticated', True):
        return fallback
    return None


def registrar_actividad(
    *,
    usuario=None,
    accion,
    modelo,
    descripcion='',
    tipo_accion=None,
    modulo='',
    objeto_id='',
    objeto_repr='',
    request=None,
    dedupe_seconds=3,
):
    from .models import LogActividad

    user = usuario_actual(usuario, request)
    tipo = tipo_accion or LogActividad(accion=accion, modelo=modelo)._inferir_tipo_accion()
    ip = get_client_ip(request)
    objeto_id = str(objeto_id or '')

    if dedupe_seconds and objeto_id:
        desde = timezone.now() - timezone.timedelta(seconds=dedupe_seconds)
        if LogActividad.objects.filter(
            modelo=modelo,
            objeto_id=objeto_id,
            tipo_accion=tipo,
            fecha__gte=desde,
        ).exists():
            return None

    return LogActividad.objects.create(
        usuario=user,
        accion=accion,
        tipo_accion=tipo,
        modelo=modelo,
        modulo=modulo,
        objeto_id=objeto_id,
        objeto_repr=str(objeto_repr or '')[:220],
        descripcion=descripcion,
        direccion_ip=ip,
    )
