from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.http import require_POST

from apps.auth_app.models import CustomUser
from apps.core.audit import registrar_actividad
from apps.core.decorators import requiere_acceso
from apps.pacientes.models import Paciente
from apps.referencias.models import ReferenciaIngresoCasaFACCI

from .entrega import (
    build_entrega_context,
    ensure_entrega_items,
    entrega_pdf_filename,
    render_entrega_pdf,
)
from .formulario import build_formulario_context, formulario_pdf_filename, render_formulario_pdf
from .models import EntregaHabitacion, EstanciaFamiliar, HabitacionCasa
from .reportes import build_reporte_estancias_context, render_reporte_estancias_pdf


@login_required
@requiere_acceso('puede_ver_alojamiento')
def lista_view(request):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    estado = request.GET.get('estado', 'ACTIVA')
    q = request.GET.get('q', '').strip()

    estancias = EstanciaFamiliar.objects.select_related(
        'paciente', 'habitacion', 'registrado_por'
    )
    if estado and estado in EstanciaFamiliar.Estado.values:
        estancias = estancias.filter(estado=estado)
    if q:
        estancias = estancias.filter(
            paciente__nombres__icontains=q
        ) | estancias.filter(paciente__apellidos__icontains=q) | estancias.filter(
            acompanante_nombre__icontains=q
        )

    estancias = estancias.distinct().order_by('-fecha_ingreso')

    # Query pending references to Casa FACCI (PENDIENTE or APROBADA)
    referencias_pendientes = ReferenciaIngresoCasaFACCI.objects.filter(
        estado__in=[
            ReferenciaIngresoCasaFACCI.Estado.PENDIENTE,
            ReferenciaIngresoCasaFACCI.Estado.APROBADA,
        ]
    ).select_related('paciente', 'habitacion', 'referencia_medica').order_by('-fecha_creacion')

    if q:
        referencias_pendientes = referencias_pendientes.filter(
            Q(paciente__nombres__icontains=q) | Q(paciente__apellidos__icontains=q)
        )

    habitaciones = HabitacionCasa.objects.filter(activa=True)
    activas = EstanciaFamiliar.objects.filter(estado=EstanciaFamiliar.Estado.ACTIVA).count()
    disponibles = sum(1 for h in habitaciones if h.disponible)
    total_hab = habitaciones.count()

    context = {
        'estancias': estancias,
        'referencias_pendientes': referencias_pendientes,
        'habitaciones': habitaciones,
        'activas': activas,
        'disponibles': disponibles,
        'total_hab': total_hab,
        'estado_actual': estado,
        'q': q,
        'estados': EstanciaFamiliar.Estado.choices,
        'primera_estancia_activa': EstanciaFamiliar.objects.filter(
            estado=EstanciaFamiliar.Estado.ACTIVA,
        ).order_by('-fecha_ingreso').first(),
    }
    return render(request, 'alojamiento/lista.html', context)


@login_required
@requiere_acceso('puede_gestionar_alojamiento')
def crear_view(request, paciente_pk=None):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    paciente_preseleccionado = None
    referencia_id = request.GET.get('referencia_id') or request.POST.get('referencia_id')
    ref_ingreso = None
    prefill_data = {}

    if referencia_id:
        ref_ingreso = get_object_or_404(ReferenciaIngresoCasaFACCI, pk=referencia_id)
        paciente_preseleccionado = ref_ingreso.paciente

        # Smart mapping of the reason for the stay based on text
        motivo_value = EstanciaFamiliar.MotivoEstancia.OTRO
        motivo_lower = (ref_ingreso.motivo_ingreso or '').lower()
        if 'quimio' in motivo_lower:
            motivo_value = EstanciaFamiliar.MotivoEstancia.QUIMIOTERAPIA
        elif any(w in motivo_lower for w in ['cirug', 'quirur', 'operac']):
            motivo_value = EstanciaFamiliar.MotivoEstancia.CIRUGIA
        elif 'radio' in motivo_lower:
            motivo_value = EstanciaFamiliar.MotivoEstancia.RADIOTERAPIA
        elif 'hosp' in motivo_lower:
            motivo_value = EstanciaFamiliar.MotivoEstancia.HOSPITALIZACION
        elif any(w in motivo_lower for w in ['consult', 'exam', 'chequeo']):
            motivo_value = EstanciaFamiliar.MotivoEstancia.CONSULTA

        prefill_data = {
            'referencia_id': referencia_id,
            'acompanante_nombre': ref_ingreso.responsable_paciente,
            'acompanante_parentesco': ref_ingreso.parentesco_responsable,
            'acompanante_telefono': ref_ingreso.telefono_responsable or ref_ingreso.celular_responsable,
            'motivo': motivo_value,
            'fecha_ingreso': ref_ingreso.fecha_entrada.isoformat() if ref_ingreso.fecha_entrada else '',
            'fecha_egreso_prevista': ref_ingreso.fecha_salida.isoformat() if ref_ingreso.fecha_salida else '',
            'habitacion_id': ref_ingreso.habitacion_id,
            'observaciones': f"Motivo de ingreso de referencia: {ref_ingreso.motivo_ingreso}\n\n{ref_ingreso.observaciones or ''}".strip()
        }
    elif paciente_pk:
        paciente_preseleccionado = get_object_or_404(Paciente, pk=paciente_pk)

    if request.method == 'POST':
        pac_id = request.POST.get('paciente', '').strip()
        hab_id = request.POST.get('habitacion', '').strip()
        fecha_ingreso = parse_date(request.POST.get('fecha_ingreso', '') or '')
        fecha_egreso_prevista = parse_date(request.POST.get('fecha_egreso_prevista', '') or '')

        errors = []
        paciente = None
        habitacion = None

        if not pac_id:
            errors.append('Seleccione un paciente.')
        else:
            try:
                paciente = Paciente.objects.get(pk=pac_id)
            except Paciente.DoesNotExist:
                errors.append('Paciente no encontrado.')

        if not hab_id:
            errors.append('Seleccione una habitación.')
        else:
            try:
                habitacion = HabitacionCasa.objects.get(pk=hab_id)
                if not habitacion.disponible:
                    errors.append(f'La habitación "{habitacion.nombre}" no tiene cupo disponible.')
            except HabitacionCasa.DoesNotExist:
                errors.append('Habitación no encontrada.')

        if not fecha_ingreso:
            errors.append('La fecha de ingreso es obligatoria.')
        if fecha_ingreso and fecha_egreso_prevista and fecha_egreso_prevista < fecha_ingreso:
            errors.append('La fecha de salida no puede ser menor que la fecha de ingreso.')
        if paciente and EstanciaFamiliar.objects.filter(
            paciente=paciente,
            estado=EstanciaFamiliar.Estado.ACTIVA,
        ).exists():
            errors.append(f'{paciente.nombre_completo} ya tiene una estancia activa en Casa FACCI.')

        if errors:
            for err in errors:
                messages.error(request, err)
            # If we submitted the form and there were errors, preserve form inputs in prefill_data
            prefill_data = {
                'referencia_id': request.POST.get('referencia_id', ''),
                'acompanante_nombre': request.POST.get('acompanante_nombre', '').strip(),
                'acompanante_parentesco': request.POST.get('acompanante_parentesco', '').strip(),
                'acompanante_telefono': request.POST.get('acompanante_telefono', '').strip(),
                'motivo': request.POST.get('motivo', ''),
                'fecha_ingreso': request.POST.get('fecha_ingreso', ''),
                'fecha_egreso_prevista': request.POST.get('fecha_egreso_prevista', ''),
                'habitacion_id': request.POST.get('habitacion', ''),
                'observaciones': request.POST.get('observaciones', '').strip(),
            }
        else:
            estancia = EstanciaFamiliar.objects.create(
                paciente=paciente,
                habitacion=habitacion,
                acompanante_nombre=request.POST.get('acompanante_nombre', '').strip(),
                acompanante_parentesco=request.POST.get('acompanante_parentesco', '').strip(),
                acompanante_telefono=request.POST.get('acompanante_telefono', '').strip(),
                motivo=request.POST.get('motivo', EstanciaFamiliar.MotivoEstancia.CONSULTA),
                fecha_ingreso=fecha_ingreso,
                fecha_egreso_prevista=fecha_egreso_prevista,
                observaciones=request.POST.get('observaciones', '').strip(),
                registrado_por=request.user,
            )

            # Update the status of the ReferenciaIngresoCasaFACCI to INGRESADO
            if referencia_id:
                ref_ingreso = ReferenciaIngresoCasaFACCI.objects.filter(pk=referencia_id).first()
                if ref_ingreso:
                    ref_ingreso.estado = ReferenciaIngresoCasaFACCI.Estado.INGRESADO
                    if not ref_ingreso.habitacion:
                        ref_ingreso.habitacion = habitacion
                    ref_ingreso.save()

            messages.success(
                request,
                f'Estancia {estancia.codigo} registrada para {paciente.nombre_completo} — {habitacion.nombre}.'
            )
            return redirect('alojamiento:detalle', pk=str(estancia.pk))

    pacientes = Paciente.objects.filter(
        estado_actual__in=[
            Paciente.EstadoPaciente.EN_TRATAMIENTO,
            Paciente.EstadoPaciente.CONFIRMADO,
            Paciente.EstadoPaciente.EN_REMISION,
        ]
    ).order_by('apellidos', 'nombres')

    context = {
        'pacientes': pacientes,
        'habitaciones': HabitacionCasa.objects.filter(activa=True),
        'motivos': EstanciaFamiliar.MotivoEstancia.choices,
        'paciente_preseleccionado': paciente_preseleccionado,
        'hoy': timezone.now().date().isoformat(),
        'prefill_data': prefill_data,
    }
    return render(request, 'alojamiento/crear.html', context)


def _estancia_formulario_queryset():
    return EstanciaFamiliar.objects.select_related(
        'paciente__padre_tutor__usuario',
        'habitacion',
        'registrado_por',
    )


@login_required
@requiere_acceso('puede_gestionar_alojamiento')
def editar_view(request, pk):
    estancia = get_object_or_404(
        EstanciaFamiliar.objects.select_related('paciente', 'habitacion'),
        pk=pk,
    )
    if estancia.estado != EstanciaFamiliar.Estado.ACTIVA:
        messages.error(request, 'Solo se pueden editar estadías activas.')
        return redirect('alojamiento:detalle', pk=pk)

    if request.method == 'POST':
        habitacion_id = request.POST.get('habitacion', '').strip()
        habitacion = HabitacionCasa.objects.filter(pk=habitacion_id, activa=True).first()
        fecha_ingreso = parse_date(request.POST.get('fecha_ingreso', '') or '')
        fecha_egreso_prevista = parse_date(request.POST.get('fecha_egreso_prevista', '') or '')
        errors = []

        if habitacion is None:
            errors.append('Seleccione una habitación válida.')
        elif habitacion != estancia.habitacion and not habitacion.disponible:
            errors.append(f'La habitación "{habitacion.nombre}" no tiene cupo disponible.')
        if not fecha_ingreso:
            errors.append('La fecha de ingreso es obligatoria.')
        if fecha_ingreso and fecha_egreso_prevista and fecha_egreso_prevista < fecha_ingreso:
            errors.append('La fecha de salida no puede ser menor que la fecha de ingreso.')

        if not errors:
            habitacion_anterior = estancia.habitacion
            estancia.habitacion = habitacion
            estancia.acompanante_nombre = request.POST.get('acompanante_nombre', '').strip()
            estancia.acompanante_parentesco = request.POST.get('acompanante_parentesco', '').strip()
            estancia.acompanante_telefono = request.POST.get('acompanante_telefono', '').strip()
            estancia.motivo = request.POST.get('motivo', estancia.motivo)
            estancia.fecha_ingreso = fecha_ingreso
            estancia.fecha_egreso_prevista = fecha_egreso_prevista
            estancia.observaciones = request.POST.get('observaciones', '').strip()
            estancia.save()
            registrar_actividad(
                usuario=request.user,
                accion='Editar Estadía Casa FACCI',
                modelo='EstanciaFamiliar',
                objeto_id=str(estancia.pk),
                objeto_repr=estancia.codigo,
                descripcion=(
                    f'Estadía actualizada para {estancia.paciente.nombre_completo}. '
                    f'Habitación: {habitacion_anterior} → {estancia.habitacion}.'
                ),
            )
            messages.success(request, f'Estadía {estancia.codigo} actualizada correctamente.')
            return redirect('alojamiento:detalle', pk=estancia.pk)

        for error in errors:
            messages.error(request, error)
        prefill_data = {
            'habitacion_id': habitacion_id,
            'acompanante_nombre': request.POST.get('acompanante_nombre', '').strip(),
            'acompanante_parentesco': request.POST.get('acompanante_parentesco', '').strip(),
            'acompanante_telefono': request.POST.get('acompanante_telefono', '').strip(),
            'motivo': request.POST.get('motivo', ''),
            'fecha_ingreso': request.POST.get('fecha_ingreso', ''),
            'fecha_egreso_prevista': request.POST.get('fecha_egreso_prevista', ''),
            'observaciones': request.POST.get('observaciones', '').strip(),
        }
    else:
        prefill_data = {
            'habitacion_id': estancia.habitacion_id,
            'acompanante_nombre': estancia.acompanante_nombre,
            'acompanante_parentesco': estancia.acompanante_parentesco,
            'acompanante_telefono': estancia.acompanante_telefono,
            'motivo': estancia.motivo,
            'fecha_ingreso': estancia.fecha_ingreso.isoformat(),
            'fecha_egreso_prevista': (
                estancia.fecha_egreso_prevista.isoformat()
                if estancia.fecha_egreso_prevista else ''
            ),
            'observaciones': estancia.observaciones,
        }

    return render(request, 'alojamiento/crear.html', {
        'es_edicion': True,
        'estancia': estancia,
        'paciente_preseleccionado': estancia.paciente,
        'pacientes': Paciente.objects.none(),
        'habitaciones': HabitacionCasa.objects.filter(activa=True),
        'motivos': EstanciaFamiliar.MotivoEstancia.choices,
        'prefill_data': prefill_data,
        'hoy': timezone.localdate().isoformat(),
    })


@login_required
@requiere_acceso('puede_ver_alojamiento')
def formulario_estancia(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    estancia = get_object_or_404(_estancia_formulario_queryset(), pk=pk)
    formulario = build_formulario_context(estancia)
    return render(
        request,
        'alojamiento/formulario_estancia.html',
        {
            'estancia': estancia,
            'formulario': formulario,
            'auto_print': request.GET.get('print') == '1',
        },
    )


@login_required
@requiere_acceso('puede_ver_alojamiento')
def formulario_estancia_pdf(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    estancia = get_object_or_404(_estancia_formulario_queryset(), pk=pk)
    formulario = build_formulario_context(estancia)
    response = HttpResponse(render_formulario_pdf(formulario), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{formulario_pdf_filename(estancia)}"'
    return response


@login_required
@requiere_acceso('puede_ver_alojamiento')
def reporte_estancias(request):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    reporte = build_reporte_estancias_context(request.user)
    return render(request, 'alojamiento/reporte_estancias.html', {'reporte': reporte})


@login_required
@requiere_acceso('puede_ver_alojamiento')
def reporte_estancias_pdf(request):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    reporte = build_reporte_estancias_context(request.user)
    response = HttpResponse(render_reporte_estancias_pdf(reporte), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_estancias_casa_facci.pdf"'
    return response


def _estancia_entrega_queryset():
    return EstanciaFamiliar.objects.select_related(
        'paciente__padre_tutor__usuario',
        'habitacion',
        'registrado_por',
    )


def _get_or_create_entrega(estancia, user):
    entrega, _created = EntregaHabitacion.objects.get_or_create(
        estancia=estancia,
        defaults={
            'creado_por': user,
            'recibido_por_familiar': estancia.acompanante_nombre,
            'entregado_por_familiar': estancia.acompanante_nombre,
        },
    )
    ensure_entrega_items(entrega)
    return entrega


@login_required
@requiere_acceso('puede_gestionar_alojamiento')
def entrega_habitacion(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    estancia = get_object_or_404(_estancia_entrega_queryset(), pk=pk)
    entrega = _get_or_create_entrega(estancia, request.user)

    if request.method == 'POST':
        entrega.fecha_entrega = parse_date(request.POST.get('fecha_entrega', '') or '') or entrega.fecha_entrega
        entrega.hora_ingreso = parse_time(request.POST.get('hora_ingreso', '') or '') or None
        entrega.hora_salida = parse_time(request.POST.get('hora_salida', '') or '') or None
        entrega.entregado_por_facci = request.POST.get('entregado_por_facci', '').strip() or 'Encargado Administrativo FACCI'
        entrega.recibido_por_familiar = request.POST.get('recibido_por_familiar', '').strip()
        entrega.entregado_por_familiar = request.POST.get('entregado_por_familiar', '').strip()
        entrega.recibido_por_facci = request.POST.get('recibido_por_facci', '').strip() or 'Encargado Administrativo FACCI'
        entrega.observaciones = request.POST.get('observaciones', '').strip()
        entrega.save()

        marcados = 0
        for item in entrega.items.all():
            entregado = request.POST.get(f'entregado_{item.pk}') == 'on'
            recibido = request.POST.get(f'recibido_{item.pk}') == 'on'
            if entregado or recibido:
                marcados += 1
            item.entregado_por_facci = entregado
            item.recibido_por_familiar = recibido
            item.observacion = request.POST.get(f'observacion_{item.pk}', '').strip()
            item.save(update_fields=['entregado_por_facci', 'recibido_por_familiar', 'observacion'])

        if marcados == 0:
            messages.warning(request, 'La entrega se guardo sin items marcados. Revise el checklist antes de imprimir.')
        messages.success(request, 'Control de entrega de habitacion guardado correctamente.')
        return redirect('alojamiento:entrega_habitacion', pk=estancia.pk)

    context = build_entrega_context(entrega)
    context['auto_print'] = request.GET.get('print') == '1'
    return render(request, 'alojamiento/entrega_habitacion.html', context)


@login_required
@requiere_acceso('puede_ver_alojamiento')
def entrega_habitacion_imprimir(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    estancia = get_object_or_404(_estancia_entrega_queryset(), pk=pk)
    entrega = _get_or_create_entrega(estancia, request.user)
    context = build_entrega_context(entrega)
    context['auto_print'] = True
    return render(request, 'alojamiento/entrega_habitacion.html', context)


@login_required
@requiere_acceso('puede_ver_alojamiento')
def entrega_habitacion_pdf(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    estancia = get_object_or_404(_estancia_entrega_queryset(), pk=pk)
    entrega = _get_or_create_entrega(estancia, request.user)
    context = build_entrega_context(entrega)
    response = HttpResponse(render_entrega_pdf(context), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{entrega_pdf_filename(entrega)}"'
    return response


@login_required
@requiere_acceso('puede_ver_alojamiento')
def detalle_view(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    estancia = get_object_or_404(
        EstanciaFamiliar.objects.select_related('paciente', 'habitacion', 'registrado_por'),
        pk=pk,
    )
    context = {
        'estancia': estancia,
        'otras_estancias': EstanciaFamiliar.objects.filter(
            paciente=estancia.paciente
        ).exclude(pk=pk).order_by('-fecha_ingreso')[:5],
    }
    return render(request, 'alojamiento/detalle.html', context)


@login_required
@requiere_acceso('puede_gestionar_alojamiento')
def checkout_view(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    estancia = get_object_or_404(EstanciaFamiliar, pk=pk)
    if estancia.estado != EstanciaFamiliar.Estado.ACTIVA:
        messages.error(request, 'Esta estancia ya está cerrada.')
        return redirect('alojamiento:detalle', pk=pk)

    if request.method == 'POST':
        accion = request.POST.get('accion', 'completar')
        fecha_egreso = parse_date(request.POST.get('fecha_egreso', '') or '') or timezone.now().date()
        estancia.fecha_egreso_real = fecha_egreso
        estancia.estado = (
            EstanciaFamiliar.Estado.COMPLETADA
            if accion == 'completar'
            else EstanciaFamiliar.Estado.CANCELADA
        )
        obs_extra = request.POST.get('observaciones_egreso', '').strip()
        if obs_extra:
            estancia.observaciones = (estancia.observaciones + '\n' + obs_extra).strip()
        estancia.save()
        messages.success(
            request,
            f'Estancia {estancia.codigo} cerrada el {fecha_egreso}. '
            f'{estancia.noches or 0} noche(s) registradas.'
        )
        return redirect('alojamiento:detalle', pk=pk)

    return render(request, 'alojamiento/checkout.html', {'estancia': estancia, 'hoy': timezone.now().date().isoformat()})


@login_required
@requiere_acceso('puede_ver_alojamiento')
def habitaciones_view(request):
    """Listado de habitaciones y alta de nuevas (CU-34)."""
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    if request.method == 'POST':
        if not request.user.puede_gestionar_alojamiento:
            messages.error(request, 'No tiene permisos para agregar habitaciones.')
            return redirect('alojamiento:habitaciones')

        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        capacidad_raw = request.POST.get('capacidad', '').strip()

        errors = []
        if not nombre:
            errors.append('El nombre / número de la habitación es obligatorio.')
        elif HabitacionCasa.objects.filter(nombre__iexact=nombre).exists():
            errors.append(f'Ya existe una habitación llamada "{nombre}".')

        try:
            capacidad = int(capacidad_raw)
            if capacidad < 1:
                errors.append('La capacidad debe ser de al menos 1 persona.')
        except (TypeError, ValueError):
            errors.append('La capacidad debe ser un número válido.')
            capacidad = None

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            HabitacionCasa.objects.create(
                nombre=nombre,
                capacidad=capacidad,
                descripcion=descripcion,
            )
            messages.success(request, f'Habitación "{nombre}" creada correctamente.')
            return redirect('alojamiento:habitaciones')

    habitaciones = HabitacionCasa.objects.all()
    context = {
        'habitaciones': habitaciones,
        'total_hab': habitaciones.count(),
        'activas_count': sum(1 for h in habitaciones if h.activa),
        'disponibles': sum(1 for h in habitaciones if h.disponible),
    }
    return render(request, 'alojamiento/habitaciones.html', context)


@login_required
@requiere_acceso('puede_gestionar_alojamiento')
@require_POST
def habitacion_toggle_view(request, pk):
    """Habilita / deshabilita una habitación (CU-35)."""
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    habitacion = get_object_or_404(HabitacionCasa, pk=pk)
    if habitacion.activa and habitacion.ocupantes_actuales > 0:
        messages.error(
            request,
            f'No se puede deshabilitar "{habitacion.nombre}": tiene '
            f'{habitacion.ocupantes_actuales} estancia(s) activa(s).'
        )
    else:
        habitacion.activa = not habitacion.activa
        habitacion.save(update_fields=['activa'])
        estado = 'habilitada' if habitacion.activa else 'deshabilitada'
        messages.success(request, f'Habitación "{habitacion.nombre}" {estado}.')
    return redirect('alojamiento:habitaciones')


@login_required
@requiere_acceso('puede_gestionar_alojamiento')
@require_POST
def habitacion_eliminar_view(request, pk):
    """Elimina una habitación si no tiene estancias asociadas (CU-36)."""
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    habitacion = get_object_or_404(HabitacionCasa, pk=pk)
    nombre = habitacion.nombre
    try:
        habitacion.delete()
        messages.success(request, f'Habitación "{nombre}" eliminada.')
    except ProtectedError:
        messages.error(
            request,
            f'No se puede eliminar "{nombre}" porque tiene estancias registradas. '
            f'Deshabilítela en su lugar para retirarla de uso.'
        )
    return redirect('alojamiento:habitaciones')
