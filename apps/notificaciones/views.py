from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from apps.auth_app.models import CustomUser

from .models import Notificacion
from .services import (
    archivar_notificacion,
    marcar_notificacion_leida,
    marcar_notificacion_no_leida,
    marcar_todas_leidas,
    registrar_apertura,
)


def _counts(user):
    base = Notificacion.objects.filter(usuario=user, archivada=False, leida=False)
    return {
        'sin_leer': base.count(),
    }


def _notification_payload(notificacion):
    return {
        'id': str(notificacion.id),
        'tipo': notificacion.tipo,
        'titulo': notificacion.titulo,
        'mensaje': notificacion.mensaje,
        'prioridad': notificacion.prioridad,
        'modulo': notificacion.modulo,
        'leida': notificacion.leida,
        'tiempo': notificacion.tiempo,
        'icono': notificacion.icono,
        'color': notificacion.color,
        'accion_url': notificacion.abrir_url if notificacion.accion_url else '',
        'accion_texto': notificacion.accion_texto,
    }


@login_required
def notificaciones_view(request):
    Notificacion.seed_for_user(request.user)
    notificaciones = Notificacion.objects.filter(usuario=request.user, archivada=False).select_related('content_type')

    estado = request.GET.get('estado', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    prioridad = request.GET.get('prioridad', '').strip()
    fecha_desde = parse_date(request.GET.get('desde', '').strip())
    fecha_hasta = parse_date(request.GET.get('hasta', '').strip())

    if estado == 'no_leidas':
        notificaciones = notificaciones.filter(leida=False)
    elif estado == 'leidas':
        notificaciones = notificaciones.filter(leida=True)
    if tipo in Notificacion.TipoNotificacion.values:
        notificaciones = notificaciones.filter(tipo=tipo)
    if prioridad in Notificacion.Prioridad.values:
        notificaciones = notificaciones.filter(prioridad=prioridad)
    if fecha_desde:
        notificaciones = notificaciones.filter(created_at__date__gte=fecha_desde)
    if fecha_hasta:
        notificaciones = notificaciones.filter(created_at__date__lte=fecha_hasta)

    paginator = Paginator(notificaciones.order_by('-created_at'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    counts = _counts(request.user)
    params = request.GET.copy()
    params.pop('page', None)

    is_parent = request.user.rol == CustomUser.Rol.PADRE_TUTOR
    return render(request, 'notificaciones/notificaciones.html', {
        'titulo_pagina': 'Notificaciones',
        'base_template': 'layouts/base_padres.html' if is_parent else 'layouts/base.html',
        'back_url': reverse('padres:estado') if is_parent else reverse('home'),
        'notificaciones': page_obj.object_list,
        'page_obj': page_obj,
        'sin_leer': counts['sin_leer'],
        'filtros': {
            'estado': estado,
            'tipo': tipo,
            'prioridad': prioridad,
            'desde': request.GET.get('desde', '').strip(),
            'hasta': request.GET.get('hasta', '').strip(),
        },
        'tipos': Notificacion.TipoNotificacion.choices,
        'prioridades': Notificacion.Prioridad.choices,
        'querystring': params.urlencode(),
    })


@login_required
@require_POST
def marcar_leida_view(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user, archivada=False)
    marcar_notificacion_leida(notificacion, usuario=request.user)
    return JsonResponse({'status': 'ok', **_counts(request.user)})


@login_required
@require_POST
def marcar_no_leida_view(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user, archivada=False)
    marcar_notificacion_no_leida(notificacion, usuario=request.user)
    return JsonResponse({'status': 'ok', **_counts(request.user)})


@login_required
@require_POST
def eliminar_notificacion_view(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user, archivada=False)
    archivar_notificacion(notificacion, usuario=request.user)
    return JsonResponse({'status': 'ok', **_counts(request.user)})


@login_required
@require_POST
def marcar_todas_leidas_view(request):
    queryset = Notificacion.objects.filter(usuario=request.user, archivada=False)
    marcar_todas_leidas(request.user, queryset=queryset)
    return JsonResponse({'status': 'ok', **_counts(request.user)})


@login_required
def abrir_notificacion_view(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk, usuario=request.user, archivada=False)
    registrar_apertura(notificacion, usuario=request.user)
    destino = notificacion.resolved_accion_url
    if destino and destino != '#':
        return redirect(destino)
    return redirect('notificaciones')


@login_required
def notificaciones_api_view(request):
    Notificacion.seed_for_user(request.user)
    notificaciones = (
        Notificacion.objects
        .filter(usuario=request.user, archivada=False)
        .order_by('-created_at')[:15]
    )
    return JsonResponse({
        'notificaciones': [_notification_payload(n) for n in notificaciones],
        'sin_leer': _counts(request.user)['sin_leer'],
    })
