from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone

from apps.core.decorators import solo_personal
from apps.pacientes.models import Paciente
from apps.auth_app.models import CustomUser
from apps.cribado.models import CuestionarioCribado
from .models import CasoClinico, NotaCaso


# ── Helpers de permisos ──────────────────────────────────────────────────────

def _puede_crear_caso(user):
    return user.rol in [
        CustomUser.Rol.ADMIN,
        CustomUser.Rol.MEDICO,
        CustomUser.Rol.PEDIATRA,
        CustomUser.Rol.ONCOLOGO,
        CustomUser.Rol.PERSONAL_FACCI,
    ]


def _puede_editar_caso(user, caso):
    if user.rol == CustomUser.Rol.ADMIN:
        return True
    if caso.medico_responsable == user:
        return True
    if caso.creado_por == user:
        return True
    return False


def _casos_visibles(user):
    if user.rol == CustomUser.Rol.ADMIN:
        return CasoClinico.objects.all()
    if user.rol == CustomUser.Rol.ONCOLOGO:
        return CasoClinico.objects.filter(
            Q(medico_responsable=user) |
            Q(paciente__referencias__especialista_destino=user)
        ).distinct()
    if user.rol in [CustomUser.Rol.MEDICO, CustomUser.Rol.PEDIATRA]:
        return CasoClinico.objects.filter(
            Q(medico_responsable=user) |
            Q(paciente__medico_asignado=user) |
            Q(paciente__creado_por=user)
        ).distinct()
    # PERSONAL_FACCI: todos
    return CasoClinico.objects.all()


def _pacientes_disponibles(user):
    if user.rol == CustomUser.Rol.ADMIN:
        return Paciente.objects.all()
    if user.rol == CustomUser.Rol.ONCOLOGO:
        return Paciente.objects.filter(
            referencias__especialista_destino=user
        ).distinct()
    if user.rol in [CustomUser.Rol.MEDICO, CustomUser.Rol.PEDIATRA]:
        return Paciente.objects.filter(
            Q(medico_asignado=user) | Q(creado_por=user)
        ).distinct()
    return Paciente.objects.all()


# ── Vistas principales ───────────────────────────────────────────────────────

@login_required
@solo_personal
def lista_view(request):
    estado_filter   = request.GET.get('estado', '')
    tipo_filter     = request.GET.get('tipo', '')
    prioridad_filter = request.GET.get('prioridad', '')
    search_query    = request.GET.get('q', '')

    casos = _casos_visibles(request.user).select_related('paciente', 'medico_responsable')

    if estado_filter:
        casos = casos.filter(estado=estado_filter)
    if tipo_filter:
        casos = casos.filter(tipo_cancer=tipo_filter)
    if prioridad_filter:
        casos = casos.filter(prioridad=prioridad_filter)
    if search_query:
        casos = casos.filter(
            Q(codigo_caso__icontains=search_query) |
            Q(titulo__icontains=search_query) |
            Q(paciente__nombres__icontains=search_query) |
            Q(paciente__apellidos__icontains=search_query)
        )

    casos = casos.order_by('-created_at')

    paginator = Paginator(casos, 12)
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)

    # Estadísticas rápidas
    todos = _casos_visibles(request.user)
    stats = {
        'total':          todos.count(),
        'activos':        todos.filter(estado__in=['ABIERTO', 'EN_ESTUDIO', 'EN_TRATAMIENTO']).count(),
        'urgentes':       todos.filter(prioridad='URGENTE').count(),
        'en_tratamiento': todos.filter(estado='EN_TRATAMIENTO').count(),
    }

    context = {
        'titulo_pagina':    'Casos Clínicos',
        'casos':            page_obj.object_list,
        'page_obj':         page_obj,
        'total':            paginator.count,
        'stats':            stats,
        'estados':          CasoClinico.EstadoCaso.choices,
        'tipos':            CasoClinico.TipoCancer.choices,
        'prioridades':      CasoClinico.Prioridad.choices,
        'filtro_estado':    estado_filter,
        'filtro_tipo':      tipo_filter,
        'filtro_prioridad': prioridad_filter,
        'filtro_search':    search_query,
    }
    return render(request, 'casos/lista.html', context)


@login_required
@solo_personal
def detalle_view(request, pk):
    caso = get_object_or_404(
        _casos_visibles(request.user).select_related(
            'paciente', 'medico_responsable', 'creado_por', 'cribado_origen'
        ),
        pk=pk,
    )
    notas = caso.notas.select_related('autor').order_by('-created_at')

    context = {
        'titulo_pagina':  f'Caso {caso.codigo_caso}',
        'caso':           caso,
        'notas':          notas,
        'puede_editar':   _puede_editar_caso(request.user, caso),
        'tipos_nota':     NotaCaso.TipoNota.choices,
    }
    return render(request, 'casos/detalle.html', context)


@login_required
@solo_personal
def crear_view(request):
    if not _puede_crear_caso(request.user):
        messages.error(request, 'No tienes permisos para crear casos clínicos.')
        return redirect('casos:lista')

    if request.method == 'POST':
        return _procesar_crear_caso(request)

    # Preseleccionar paciente si viene por querystring
    paciente_id = request.GET.get('paciente')
    cribado_id  = request.GET.get('cribado')

    context = {
        'titulo_pagina':   'Nuevo Caso Clínico',
        'pacientes':       _pacientes_disponibles(request.user).order_by('nombres', 'apellidos'),
        'medicos':         CustomUser.objects.filter(
                               rol__in=['MEDICO', 'PEDIATRA', 'ONCOLOGO', 'PERSONAL_FACCI'],
                               is_active=True
                           ).order_by('first_name', 'last_name'),
        'estados':         CasoClinico.EstadoCaso.choices,
        'tipos':           CasoClinico.TipoCancer.choices,
        'prioridades':     CasoClinico.Prioridad.choices,
        'paciente_id':     paciente_id,
        'cribado_id':      cribado_id,
        'today':           timezone.now().date().isoformat(),
    }
    return render(request, 'casos/crear.html', context)


def _procesar_crear_caso(request):
    try:
        paciente_id         = request.POST.get('paciente')
        medico_id           = request.POST.get('medico_responsable')
        titulo              = request.POST.get('titulo', '').strip()
        tipo_cancer         = request.POST.get('tipo_cancer')
        estado              = request.POST.get('estado', CasoClinico.EstadoCaso.ABIERTO)
        prioridad           = request.POST.get('prioridad', CasoClinico.Prioridad.MEDIA)
        resumen_clinico     = request.POST.get('resumen_clinico', '').strip()
        protocolo           = request.POST.get('protocolo_tratamiento', '').strip()
        observaciones       = request.POST.get('observaciones', '').strip()
        fecha_apertura      = request.POST.get('fecha_apertura')
        cribado_id          = request.POST.get('cribado_origen') or None

        if not all([paciente_id, medico_id, titulo, tipo_cancer, fecha_apertura, resumen_clinico]):
            messages.error(request, 'Completa todos los campos obligatorios.')
            return redirect('casos:crear')

        paciente = get_object_or_404(Paciente, id=paciente_id)
        medico   = get_object_or_404(CustomUser, id=medico_id)
        cribado  = get_object_or_404(CuestionarioCribado, id=cribado_id) if cribado_id else None

        caso = CasoClinico.objects.create(
            paciente=paciente,
            medico_responsable=medico,
            creado_por=request.user,
            cribado_origen=cribado,
            titulo=titulo,
            tipo_cancer=tipo_cancer,
            estado=estado,
            prioridad=prioridad,
            resumen_clinico=resumen_clinico,
            protocolo_tratamiento=protocolo,
            observaciones=observaciones,
            fecha_apertura=fecha_apertura,
        )
        messages.success(request, f'Caso {caso.codigo_caso} creado correctamente.')
        return redirect('casos:detalle', pk=caso.pk)

    except Exception as e:
        messages.error(request, f'Error al crear el caso: {str(e)}')
        return redirect('casos:crear')


@login_required
@solo_personal
def editar_view(request, pk):
    caso = get_object_or_404(CasoClinico, pk=pk)

    if not _puede_editar_caso(request.user, caso):
        messages.error(request, 'No tienes permisos para editar este caso.')
        return redirect('casos:detalle', pk=pk)

    if request.method == 'POST':
        return _procesar_editar_caso(request, caso)

    context = {
        'titulo_pagina': f'Editar {caso.codigo_caso}',
        'caso':          caso,
        'medicos':       CustomUser.objects.filter(
                             rol__in=['MEDICO', 'PEDIATRA', 'ONCOLOGO', 'PERSONAL_FACCI'],
                             is_active=True
                         ).order_by('first_name', 'last_name'),
        'estados':       CasoClinico.EstadoCaso.choices,
        'tipos':         CasoClinico.TipoCancer.choices,
        'prioridades':   CasoClinico.Prioridad.choices,
    }
    return render(request, 'casos/editar.html', context)


def _procesar_editar_caso(request, caso):
    try:
        medico_id       = request.POST.get('medico_responsable')
        titulo          = request.POST.get('titulo', '').strip()
        tipo_cancer     = request.POST.get('tipo_cancer')
        estado          = request.POST.get('estado')
        prioridad       = request.POST.get('prioridad')
        resumen_clinico = request.POST.get('resumen_clinico', '').strip()
        protocolo       = request.POST.get('protocolo_tratamiento', '').strip()
        observaciones   = request.POST.get('observaciones', '').strip()
        fecha_cierre    = request.POST.get('fecha_cierre') or None

        if not all([medico_id, titulo, tipo_cancer, estado, prioridad]):
            messages.error(request, 'Completa todos los campos obligatorios.')
            return redirect('casos:editar', pk=caso.pk)

        caso.medico_responsable   = get_object_or_404(CustomUser, id=medico_id)
        caso.titulo               = titulo
        caso.tipo_cancer          = tipo_cancer
        caso.estado               = estado
        caso.prioridad            = prioridad
        caso.resumen_clinico      = resumen_clinico
        caso.protocolo_tratamiento = protocolo
        caso.observaciones        = observaciones
        caso.fecha_cierre         = fecha_cierre
        caso.save()

        messages.success(request, f'Caso {caso.codigo_caso} actualizado.')
        return redirect('casos:detalle', pk=caso.pk)

    except Exception as e:
        messages.error(request, f'Error al actualizar: {str(e)}')
        return redirect('casos:editar', pk=caso.pk)


# ── Notas del caso ────────────────────────────────────────────────────────────

@login_required
@solo_personal
@require_POST
def agregar_nota_view(request, pk):
    caso = get_object_or_404(CasoClinico, pk=pk)

    if not _puede_editar_caso(request.user, caso):
        messages.error(request, 'No tienes permisos para agregar notas a este caso.')
        return redirect('casos:detalle', pk=pk)

    tipo         = request.POST.get('tipo', NotaCaso.TipoNota.OBSERVACION)
    titulo       = request.POST.get('titulo', '').strip()
    contenido    = request.POST.get('contenido', '').strip()
    importante   = request.POST.get('es_importante') == 'on'

    if not titulo or not contenido:
        messages.error(request, 'El título y contenido son obligatorios.')
        return redirect('casos:detalle', pk=pk)

    NotaCaso.objects.create(
        caso=caso,
        autor=request.user,
        tipo=tipo,
        titulo=titulo,
        contenido=contenido,
        es_importante=importante,
    )
    messages.success(request, 'Nota agregada correctamente.')
    return redirect('casos:detalle', pk=pk)


@login_required
@solo_personal
@require_POST
def eliminar_nota_view(request, pk, nota_pk):
    nota = get_object_or_404(NotaCaso, pk=nota_pk, caso__pk=pk)

    if request.user.rol != CustomUser.Rol.ADMIN and nota.autor != request.user:
        messages.error(request, 'Solo puedes eliminar tus propias notas.')
        return redirect('casos:detalle', pk=pk)

    nota.delete()
    messages.success(request, 'Nota eliminada.')
    return redirect('casos:detalle', pk=pk)


@login_required
@solo_personal
@require_POST
def cerrar_caso_view(request, pk):
    caso = get_object_or_404(CasoClinico, pk=pk)

    if not _puede_editar_caso(request.user, caso):
        messages.error(request, 'No tienes permisos para cerrar este caso.')
        return redirect('casos:detalle', pk=pk)

    caso.estado = CasoClinico.EstadoCaso.CERRADO
    caso.fecha_cierre = timezone.now().date()
    caso.save(update_fields=['estado', 'fecha_cierre', 'updated_at'])

    NotaCaso.objects.create(
        caso=caso,
        autor=request.user,
        tipo=NotaCaso.TipoNota.CIERRE,
        titulo='Caso cerrado',
        contenido=request.POST.get('motivo_cierre', 'Caso cerrado por el médico responsable.'),
    )

    messages.success(request, f'Caso {caso.codigo_caso} cerrado.')
    return redirect('casos:detalle', pk=pk)
