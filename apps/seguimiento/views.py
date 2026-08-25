from django.contrib.auth.decorators import login_required
import datetime
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from apps.core.audit import registrar_actividad
from apps.core.decorators import requiere_acceso
from apps.core.models import CentroSalud
from apps.auth_app.models import CustomUser
from apps.pacientes.models import Paciente
from .descargo import build_descargo_context, descargo_pdf_filename, render_descargo_pdf
from .models import SeguimientoPaciente, IndicacionMedica


_MESES_CORTOS = {
    1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic',
}


def _fmt_fecha(dt):
    if not dt:
        return '—'
    return f"{dt.day} {_MESES_CORTOS.get(dt.month, '')}, {dt.year}"


def _fmt_hora(dt):
    if not dt:
        return '—'
    return dt.strftime('%I:%M %p').lstrip('0')


def _telefono_href(valor):
    return ''.join(c for c in (valor or '') if c.isdigit() or c == '+')


def _usuario_puede_ver_paciente(user, paciente):
    if user.rol in [
        CustomUser.Rol.ADMIN,
        CustomUser.Rol.PERSONAL_FACCI,
        CustomUser.Rol.TRABAJADORA_SOCIAL,
        CustomUser.Rol.ENFERMERA,
    ]:
        return True
    if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        return paciente.medico_asignado == user or paciente.creado_por == user
    if user.rol == CustomUser.Rol.ONCOLOGO:
        return paciente.referencias.filter(especialista_destino=user).exists()
    return False


def _paciente_indicaciones_autorizado(request, paciente_id):
    paciente = get_object_or_404(
        Paciente.objects.select_related('medico_asignado', 'padre_tutor__usuario'),
        id=paciente_id,
    )
    if not _usuario_puede_ver_paciente(request.user, paciente):
        messages.error(request, 'No tiene permiso para ver las indicaciones de este paciente.')
        return paciente, False
    return paciente, True


def _build_eventos_timeline(paciente):
    """Agrega eventos de múltiples querysets en timeline unificada, orden descendente."""
    from apps.cribado.models import CuestionarioCribado
    from apps.referencias.models import ReferenciaMedica
    from apps.pacientes.models import NotaClinica

    raw = []  # list of (datetime, dict)
    score_maximo = len(CuestionarioCribado.CAMPOS_SINTOMAS)

    # Cribados
    for c in paciente.cribados.select_related('medico').all():
        color = 'error' if c.nivel_riesgo == 'ALTO' else ('secondary' if c.nivel_riesgo == 'MEDIO' else 'primary')
        raw.append((c.fecha_evaluacion, {
            'fecha': _fmt_fecha(c.fecha_evaluacion),
            'hora': _fmt_hora(c.fecha_evaluacion),
            'tipo': 'Cribado FACCI',
            'descripcion': c.observaciones or f'Puntaje: {c.puntaje_total}/{score_maximo} — {c.get_nivel_riesgo_display()}',
            'medico': c.medico.nombre_completo if c.medico else 'Sistema',
            'icono': 'fact_check',
            'color': color,
        }))

    # Referencias médicas
    for r in paciente.referencias.select_related('medico_referente').all():
        color = 'error' if r.prioridad in ['URGENTE', 'ALTA'] else 'secondary'
        raw.append((r.fecha_referencia, {
            'fecha': _fmt_fecha(r.fecha_referencia),
            'hora': _fmt_hora(r.fecha_referencia),
            'tipo': 'Referencia Médica',
            'descripcion': f'Referencia a {r.hospital_destino.nombre if r.hospital_destino else "destino sin asignar"}. {r.motivo_referencia[:120]}',
            'medico': r.medico_referente.nombre_completo if r.medico_referente else '—',
            'icono': 'send',
            'color': color,
        }))

    # Seguimientos clínicos
    for s in paciente.seguimientos.select_related('medico').all():
        color = 'error' if s.requiere_hospitalizacion else 'tertiary'
        desc = s.observaciones or s.sintomas_actuales or s.tratamiento_actual or s.estado_clinico
        raw.append((s.fecha_seguimiento, {
            'fecha': _fmt_fecha(s.fecha_seguimiento),
            'hora': _fmt_hora(s.fecha_seguimiento),
            'tipo': 'Consulta Clínica',
            'descripcion': desc,
            'medico': s.medico.nombre_completo if s.medico else '—',
            'icono': 'monitor_heart',
            'color': color,
        }))

    # Notas clínicas
    _tipo_map = {
        'EVOLUCION':   ('Evolución',      'edit_note',      'tertiary'),
        'DIAGNOSTICO': ('Diagnóstico',    'local_hospital', 'primary'),
        'TRATAMIENTO': ('Tratamiento',    'medication',     'secondary'),
        'OBSERVACION': ('Observación',    'note_alt',       'tertiary'),
        'ALERTA':      ('Alerta Clínica', 'warning',        'error'),
    }
    for n in paciente.notas_clinicas.select_related('autor').all():
        label, icono, color = _tipo_map.get(n.tipo, ('Nota', 'note_alt', 'tertiary'))
        if n.es_importante:
            color = 'error'
        raw.append((n.created_at, {
            'fecha': _fmt_fecha(n.created_at),
            'hora': _fmt_hora(n.created_at),
            'tipo': label,
            'descripcion': n.texto[:200],
            'medico': n.autor_nombre,
            'icono': icono,
            'color': color,
        }))

    raw.sort(
        key=lambda x: x[0] if x[0] else datetime.datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return [ev for _, ev in raw]


def _build_consultas_recientes(paciente, limit=3):
    """Últimas N consultas de SeguimientoPaciente para el widget de seguimiento."""
    consultas = []
    for s in paciente.seguimientos.select_related('medico').order_by('-fecha_seguimiento')[:limit]:
        proxima = s.proxima_fecha_seguimiento.strftime('%d %b') if s.proxima_fecha_seguimiento else '—'
        consultas.append({
            'fecha': _fmt_fecha(s.fecha_seguimiento),
            'tipo': s.get_fase_protocolo_display() if s.fase_protocolo else 'Consulta',
            'resumen': s.estado_clinico or s.observaciones or '—',
            'medico': s.medico.nombre_completo if s.medico else '—',
            'proxima': proxima,
        })
    return consultas


def get_paciente_seguimiento(user):
    """Retorna dict con datos del paciente activo para el usuario, o None si no existe."""
    if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        paciente = Paciente.objects.filter(
            Q(medico_asignado=user) | Q(creado_por=user)
        ).select_related('medico_asignado').first()
    elif user.rol == CustomUser.Rol.ONCOLOGO:
        paciente = Paciente.objects.filter(
            referencias__especialista_destino=user
        ).select_related('medico_asignado').distinct().first()
    else:
        paciente = Paciente.objects.select_related('medico_asignado').first()

    if not paciente:
        return None

    return {
        'id': str(paciente.id),
        'nombre': paciente.nombre_completo,
        'edad': paciente.edad,
        'diagnostico': paciente.get_diagnostico_display() if paciente.diagnostico else paciente.get_estado_actual_display(),
        'medico': paciente.medico,
        'estado': paciente.get_estado_actual_display(),
        'estado_color': paciente.estado_color,
        'iniciales': paciente.iniciales,
        'fecha_inicio': paciente.fecha,
    }


@login_required
@requiere_acceso('puede_ver_seguimiento')
def lista_view(request):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    # Un seguimiento por paciente: el más reciente
    seen = set()
    latest = []

    qs = SeguimientoPaciente.objects.select_related('paciente', 'medico')

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO, CustomUser.Rol.ENFERMERA]:
        qs = qs.filter(
            Q(paciente__medico_asignado=request.user) | Q(paciente__creado_por=request.user)
        )
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        qs = qs.filter(
            paciente__referencias__especialista_destino=request.user
        ).distinct()

    search_query = request.GET.get('q', '').strip()
    if search_query:
        qs = qs.filter(
            Q(paciente__nombres__icontains=search_query) |
            Q(paciente__apellidos__icontains=search_query) |
            Q(paciente__codigo_paciente__icontains=search_query) |
            Q(estado_clinico__icontains=search_query) |
            Q(tratamiento_actual__icontains=search_query)
        )

    qs = qs.order_by('paciente_id', '-fecha_seguimiento')

    for s in qs:
        if s.paciente_id not in seen:
            seen.add(s.paciente_id)
            latest.append(s)

    ahora = timezone.now()
    for s in latest:
        if not s.proxima_fecha_seguimiento or s.proxima_fecha_seguimiento < ahora:
            s.proxima_fecha_seguimiento = None

    FP = SeguimientoPaciente.FaseProtocolo
    paginator = Paginator(latest, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    page_list = list(page_obj)
    return render(
        request,
        'seguimiento/lista.html',
        {
            'titulo_pagina': 'Seguimiento Clinico',
            'total': len(latest),
            'page_obj': page_obj,
            'induccion':     [s for s in page_list if s.fase_protocolo == FP.INDUCCION],
            'consolidacion': [s for s in page_list if s.fase_protocolo == FP.CONSOLIDACION],
            'mantenimiento': [s for s in page_list if s.fase_protocolo == FP.MANTENIMIENTO],
            'vigilancia':    [s for s in page_list if s.fase_protocolo == FP.VIGILANCIA],
            'filtro_search': search_query,
        },
    )


@login_required
@requiere_acceso('puede_ver_seguimiento')
def seguimiento_view(request):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    paciente_data = get_paciente_seguimiento(request.user)
    paciente_obj = Paciente.objects.filter(id=paciente_data['id']).first() if paciente_data else None

    context = {
        'titulo_pagina': 'Seguimiento Clínico',
        'paciente': paciente_data,
        'consultas': _build_consultas_recientes(paciente_obj) if paciente_obj else [],
        'alertas': [],
    }
    return render(request, 'seguimiento/seguimiento.html', context)


@login_required
@requiere_acceso('puede_ver_seguimiento')
def timeline_view(request):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    paciente_data = get_paciente_seguimiento(request.user)
    paciente_obj = Paciente.objects.filter(id=paciente_data['id']).first() if paciente_data else None

    context = {
        'titulo_pagina': 'Timeline del Paciente',
        'paciente': paciente_data,
        'eventos': _build_eventos_timeline(paciente_obj) if paciente_obj else [],
    }
    return render(request, 'seguimiento/timeline.html', context)


@login_required
@requiere_acceso('puede_ver_indicaciones')
def indicaciones_admin_view(request):
    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        pacientes = Paciente.objects.filter(
            Q(medico_asignado=request.user) | Q(creado_por=request.user)
        ).select_related('medico_asignado')
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        pacientes = Paciente.objects.filter(
            referencias__especialista_destino=request.user
        ).distinct().select_related('medico_asignado')
    else:
        pacientes = Paciente.objects.select_related('medico_asignado').all()

    pacientes_data = []
    for p in pacientes:
        ultimo_seguimiento = p.seguimientos.order_by('-fecha_seguimiento').first()
        pacientes_data.append({
            'paciente': p,
            'ultimo_seguimiento': ultimo_seguimiento,
            'has_indicaciones': bool(ultimo_seguimiento and (ultimo_seguimiento.tratamiento_actual or ultimo_seguimiento.observaciones)),
            'fecha_actualizacion': ultimo_seguimiento.fecha_seguimiento.strftime('%d/%m/%Y') if ultimo_seguimiento else 'Sin registros',
        })

    context = {
        'titulo_pagina': 'Indicaciones Médicas',
        'pacientes_data': pacientes_data,
        'total_pacientes': len(pacientes_data),
        'definidos': sum(1 for x in pacientes_data if x['has_indicaciones']),
        'pendientes': sum(1 for x in pacientes_data if not x['has_indicaciones']),
    }
    return render(request, 'seguimiento/indicaciones_admin.html', context)


@login_required
@requiere_acceso('puede_ver_indicaciones')
def indicaciones_paciente_view(request, paciente_id):
    paciente, autorizado = _paciente_indicaciones_autorizado(request, paciente_id)
    if not autorizado:
        return redirect('seguimiento:indicaciones_admin')

    indicaciones = list(
        paciente.indicaciones_medicas
        .select_related('medico')
        .order_by('-activa', 'prioridad', '-created_at')
    )
    seguimientos = list(
        paciente.seguimientos
        .select_related('medico')
        .order_by('-fecha_seguimiento')
    )
    protocolo_activo = next((s for s in seguimientos if s.tratamiento_actual), None)
    pauta_medica = next((s for s in seguimientos if s.observaciones), None)

    context = {
        'titulo_pagina': f'Indicaciones - {paciente.nombre_completo}',
        'paciente': paciente,
        'indicaciones': indicaciones,
        'seguimientos': seguimientos,
        'protocolo_activo': protocolo_activo,
        'pauta_medica': pauta_medica,
        'ultima_actualizacion': seguimientos[0].fecha_seguimiento if seguimientos else None,
    }
    return render(request, 'seguimiento/paciente_indicaciones.html', context)


@login_required
@requiere_acceso('puede_ver_indicaciones')
def descargo_tratamiento_view(request, paciente_id):
    paciente, autorizado = _paciente_indicaciones_autorizado(request, paciente_id)
    if not autorizado:
        return redirect('seguimiento:indicaciones_admin')

    descargo = build_descargo_context(paciente)
    return render(
        request,
        'seguimiento/descargo_tratamiento.html',
        {
            'titulo_pagina': f'Descargo - {paciente.nombre_completo}',
            'paciente': paciente,
            'descargo': descargo,
            'auto_print': request.GET.get('print') == '1',
        },
    )


@login_required
@requiere_acceso('puede_ver_indicaciones')
def descargo_tratamiento_pdf_view(request, paciente_id):
    paciente, autorizado = _paciente_indicaciones_autorizado(request, paciente_id)
    if not autorizado:
        return redirect('seguimiento:indicaciones_admin')

    descargo = build_descargo_context(paciente)
    response = HttpResponse(render_descargo_pdf(descargo), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{descargo_pdf_filename(paciente)}"'
    return response


@login_required
@requiere_acceso('puede_gestionar_indicaciones')
def indicaciones_admin_editar_view(request, paciente_id):
    roles_sin_autoridad_clinica = [
        CustomUser.Rol.PERSONAL_FACCI,
        CustomUser.Rol.TRABAJADORA_SOCIAL,
        CustomUser.Rol.ENFERMERA,
    ]
    if request.user.rol in roles_sin_autoridad_clinica:
        messages.error(request, 'Su rol no tiene autorización para crear o editar indicaciones médicas.')
        return redirect('seguimiento:indicaciones_admin')

    paciente = get_object_or_404(Paciente, id=paciente_id)

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        if paciente.medico_asignado != request.user and paciente.creado_por != request.user:
            messages.error(request, 'No tiene permiso para editar las indicaciones de este paciente.')
            return redirect('seguimiento:indicaciones_admin')
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        if not paciente.referencias.filter(especialista_destino=request.user).exists():
            messages.error(request, 'No tiene permiso para editar las indicaciones de este paciente.')
            return redirect('seguimiento:indicaciones_admin')

    ultimo_seguimiento = paciente.seguimientos.order_by('-fecha_seguimiento').first()

    if request.method == 'POST':
        tratamiento = request.POST.get('tratamiento_actual', '').strip()
        observaciones = request.POST.get('observaciones', '').strip()
        try:
            peso_kg = float(request.POST.get('peso_kg', '').strip() or 0) or None
        except (ValueError, TypeError):
            peso_kg = None
        try:
            talla_cm = float(request.POST.get('talla_cm', '').strip() or 0) or None
        except (ValueError, TypeError):
            talla_cm = None

        hoy = timezone.now().date()
        if ultimo_seguimiento and ultimo_seguimiento.fecha_seguimiento.date() == hoy and ultimo_seguimiento.medico == request.user:
            ultimo_seguimiento.tratamiento_actual = tratamiento
            ultimo_seguimiento.observaciones = observaciones
            if peso_kg is not None:
                ultimo_seguimiento.peso_kg = peso_kg
            if talla_cm is not None:
                ultimo_seguimiento.talla_cm = talla_cm
            ultimo_seguimiento.save()
        else:
            estado = ultimo_seguimiento.estado_clinico if ultimo_seguimiento else paciente.get_estado_actual_display()
            ultimo_seguimiento = SeguimientoPaciente.objects.create(
                paciente=paciente,
                medico=request.user,
                estado_clinico=estado,
                tratamiento_actual=tratamiento,
                observaciones=observaciones,
                peso_kg=peso_kg,
                talla_cm=talla_cm,
            )

        registrar_actividad(
            usuario=request.user,
            accion='Actualizar Indicaciones',
            modelo='Paciente',
            objeto_id=str(paciente.id),
            objeto_repr=paciente.nombre_completo,
            descripcion=f'Indicaciones actualizadas para el paciente {paciente.nombre_completo}'
        )

        messages.success(request, f'Indicaciones de {paciente.nombre_completo} actualizadas correctamente.')
        return redirect('seguimiento:indicaciones_admin')

    tratamiento_actual = ultimo_seguimiento.tratamiento_actual if ultimo_seguimiento else ''
    observaciones = ultimo_seguimiento.observaciones if ultimo_seguimiento else ''
    ultimo_peso = ultimo_seguimiento.peso_kg if ultimo_seguimiento else None
    ultima_talla = ultimo_seguimiento.talla_cm if ultimo_seguimiento else None
    historial_nutricional = list(
        paciente.seguimientos
        .exclude(peso_kg__isnull=True)
        .order_by('-fecha_seguimiento')
        .values('fecha_seguimiento', 'peso_kg', 'talla_cm')[:10]
    )

    from apps.core.constants import RESTRICCIONES_GENERALES
    _ind_db = paciente.indicaciones_medicas.filter(activa=True).order_by('prioridad', '-created_at')
    indicaciones_estaticas = [
        {
            'titulo': i.titulo,
            'descripcion': i.descripcion,
            'icono': i.icono,
            'prioridad': i.get_prioridad_display(),
        }
        for i in _ind_db
    ]
    restricciones = RESTRICCIONES_GENERALES
    tutor = paciente.padre_tutor
    contactos_tutores = []
    telefono_tutor = (tutor.usuario.telefono or '').strip() if tutor and tutor.usuario else ''
    if telefono_tutor:
        contactos_tutores.append({
            'nombre': tutor.usuario.nombre_completo,
            'relacion': tutor.get_parentesco_display(),
            'telefono': telefono_tutor,
            'href': _telefono_href(telefono_tutor),
            'tipo': 'Tutor principal',
        })
    telefono_emergencia = (tutor.telefono_emergencia or '').strip() if tutor else ''
    if telefono_emergencia:
        contactos_tutores.append({
            'nombre': tutor.contacto_emergencia or 'Contacto de emergencia',
            'relacion': 'Emergencia',
            'telefono': telefono_emergencia,
            'href': _telefono_href(telefono_emergencia),
            'tipo': 'Emergencia',
        })

    context = {
        'titulo_pagina': f'Editar Indicaciones — {paciente.nombre_completo}',
        'paciente': paciente,
        'tratamiento_actual': tratamiento_actual,
        'observaciones': observaciones,
        'fecha_actualizacion': ultimo_seguimiento.fecha_seguimiento.strftime('%d %b, %Y') if ultimo_seguimiento else 'Sin registros',
        'indicaciones_estaticas': indicaciones_estaticas,
        'restricciones': restricciones,
        'contactos_tutores': contactos_tutores,
        'ultimo_peso': ultimo_peso,
        'ultima_talla': ultima_talla,
        'historial_nutricional': historial_nutricional,
    }
    return render(request, 'seguimiento/indicaciones_admin_editar.html', context)


@login_required
@requiere_acceso('puede_ver_seguimiento')
def registrar_seguimiento_view(request):
    if request.user.rol not in [CustomUser.Rol.MEDICO, CustomUser.Rol.PEDIATRA, CustomUser.Rol.ONCOLOGO, CustomUser.Rol.ADMIN]:
        messages.error(request, 'No tienes autorización para registrar seguimientos clínicos.')
        return redirect('seguimiento:lista')

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        pacientes_qs = Paciente.objects.filter(
            Q(medico_asignado=request.user) | Q(creado_por=request.user)
        )
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        pacientes_qs = Paciente.objects.filter(
            referencias__especialista_destino=request.user
        ).distinct()
    else:
        pacientes_qs = Paciente.objects.all()

    pacientes = pacientes_qs.order_by('nombres', 'apellidos')

    if request.method == 'POST':
        paciente_id = request.POST.get('paciente', '').strip()
        proxima_fecha_str = request.POST.get('proxima_fecha_seguimiento', '').strip()
        observaciones = request.POST.get('observaciones', '').strip()
        medico_id = request.POST.get('medico_seguimiento', '').strip()
        lugar_id = request.POST.get('lugar_seguimiento', '').strip()
        lugar = CentroSalud.objects.filter(pk=lugar_id).first() if lugar_id else None

        try:
            peso_kg = float(request.POST.get('peso_kg', '').strip() or 0) or None
        except (ValueError, TypeError):
            peso_kg = None
        try:
            talla_cm = float(request.POST.get('talla_cm', '').strip() or 0) or None
        except (ValueError, TypeError):
            talla_cm = None
        try:
            temperatura_c = float(request.POST.get('temperatura_c', '').strip() or 0) or None
        except (ValueError, TypeError):
            temperatura_c = None
        tension_arterial = request.POST.get('tension_arterial', '').strip()

        paciente = get_object_or_404(pacientes, pk=paciente_id)

        from django.utils.dateparse import parse_datetime
        from django.utils.timezone import make_aware, is_naive
        proxima_dt = parse_datetime(proxima_fecha_str)
        if not proxima_dt:
            messages.error(request, 'Fecha de próximo seguimiento inválida. Selecciona fecha y hora.')
            return redirect('seguimiento:registrar')
        if is_naive(proxima_dt):
            proxima_dt = make_aware(proxima_dt)
        if proxima_dt < timezone.now():
            messages.error(request, 'La fecha de la cita no puede ser en el pasado.')
            return redirect('seguimiento:registrar')

        medico_seguimiento = None
        if medico_id:
            medico_seguimiento = CustomUser.objects.filter(pk=medico_id).first()

        from apps.seguimiento.services import registrar_seguimiento
        seguimiento = registrar_seguimiento(
            paciente=paciente,
            autor=request.user,
            estado_clinico=paciente.get_estado_actual_display(),
            observaciones=observaciones,
            proxima_fecha_seguimiento=proxima_dt,
            medico_seguimiento=medico_seguimiento,
            lugar_seguimiento=lugar,
            peso_kg=peso_kg,
            talla_cm=talla_cm,
            temperatura_c=temperatura_c,
            tension_arterial=tension_arterial,
        )
        for alerta in seguimiento.alertas_valores_atipicos:
            messages.warning(request, alerta)
        messages.success(request, 'Seguimiento clínico registrado correctamente.')
        return redirect('seguimiento:lista')

    paciente_preseleccionado_id = request.GET.get('paciente_id', '').strip()
    medicos_disponibles = CustomUser.objects.filter(
        rol__in=['MEDICO', 'PEDIATRA', 'ONCOLOGO', 'PERSONAL_FACCI']
    ).order_by('first_name')
    centros_disponibles = CentroSalud.objects.filter(activo=True).order_by('nombre')

    context = {
        'titulo_pagina': 'Registrar Seguimiento Clínico',
        'pacientes': pacientes,
        'paciente_preseleccionado_id': paciente_preseleccionado_id,
        'medicos_disponibles': medicos_disponibles,
        'centros_disponibles': centros_disponibles,
    }
    return render(request, 'seguimiento/registrar_seguimiento.html', context)
