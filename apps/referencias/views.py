import uuid
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.alojamiento.models import EstanciaFamiliar, HabitacionCasa
from apps.auth_app.models import CustomUser
from apps.core.audit import registrar_actividad
from apps.core.decorators import requiere_acceso
from apps.core.models import CentroSalud, LogActividad
from apps.cribado.models import CuestionarioCribado
from apps.pacientes.models import Paciente

from .ingreso_casa import build_ingreso_casa_context, ingreso_pdf_filename, render_ingreso_casa_pdf
from .models import Contrarreferencia, ReferenciaIngresoCasaFACCI, ReferenciaMedica


_ESPECIALIDADES_FALLBACK = [
    'Oncologia Pediatrica',
    'Hematologia',
    'Neurologia Pediatrica',
    'Cirugia Pediatrica',
    'Radioterapia',
    'Nefrologia',
]

def _get_especialidades():
    qs = list(
        CustomUser.objects.filter(
            rol__in=[
                CustomUser.Rol.ONCOLOGO,
                CustomUser.Rol.PEDIATRA,
                CustomUser.Rol.MEDICO,
            ]
        )
        .exclude(especialidad='')
        .values_list('especialidad', flat=True)
        .distinct()
        .order_by('especialidad')
    )
    return qs if qs else _ESPECIALIDADES_FALLBACK


def _especialistas_queryset(excluir_usuario=None):
    # Solo roles clínicos con permiso para gestionar/recibir referencias
    # (puede_gestionar_referencias). Excluye al Coordinador FACCI, Trabajo
    # Social, Enfermería y Padre/Tutor, que no gestionan referencias.
    qs = CustomUser.objects.filter(
        rol__in=[
            CustomUser.Rol.ONCOLOGO,
            CustomUser.Rol.PEDIATRA,
            CustomUser.Rol.MEDICO,
        ]
    ).order_by('first_name', 'last_name', 'username')
    # No permitir referirse a sí mismo: excluir al usuario logueado.
    if excluir_usuario is not None and getattr(excluir_usuario, 'pk', None):
        qs = qs.exclude(pk=excluir_usuario.pk)
    return qs


def _pacientes_queryset_para_usuario(user):
    if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO, CustomUser.Rol.ENFERMERA]:
        return Paciente.objects.filter(Q(medico_asignado=user) | Q(creado_por=user)).distinct()
    if user.rol == CustomUser.Rol.ONCOLOGO:
        return Paciente.objects.filter(
            Q(referencias__especialista_destino=user) |
            Q(referencias__medico_referente=user) |
            Q(medico_asignado=user)
        ).distinct()
    return Paciente.objects.all()


def _usuario_puede_ver_paciente(user, paciente):
    if user.rol == CustomUser.Rol.PADRE_TUTOR:
        return False
    if user.rol in [CustomUser.Rol.ADMIN, CustomUser.Rol.PERSONAL_FACCI, CustomUser.Rol.TRABAJADORA_SOCIAL]:
        return True
    if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO, CustomUser.Rol.ENFERMERA]:
        return paciente.medico_asignado == user or paciente.creado_por == user
    if user.rol == CustomUser.Rol.ONCOLOGO:
        return (
            paciente.medico_asignado == user or
            paciente.referencias.filter(Q(especialista_destino=user) | Q(medico_referente=user)).exists() or
            paciente.referencias.filter(
                especialista_destino__isnull=True,
                estado=ReferenciaMedica.EstadoReferencia.PENDIENTE,
                prioridad=ReferenciaMedica.Prioridad.URGENTE,
            ).exists()
        )
    return False


def _usuario_puede_ver_ingreso(user, ingreso):
    paciente = ingreso.paciente
    if _usuario_puede_ver_paciente(user, paciente):
        return True
    referencia = ingreso.referencia_medica
    if referencia:
        return referencia.medico_referente == user or referencia.especialista_destino == user
    return ingreso.creado_por == user


def _parse_fecha_cita(valor):
    if not valor:
        return None
    fecha_hora = parse_datetime(valor)
    if fecha_hora:
        if timezone.is_naive(fecha_hora):
            return timezone.make_aware(fecha_hora)
        return fecha_hora
    fecha = parse_date(valor)
    if fecha:
        return timezone.make_aware(datetime.datetime.combine(fecha, datetime.time.min))
    return None


def _motivo_desde_cribado(cribado):
    positivos = [
        cribado._meta.get_field(campo).verbose_name
        for campo in CuestionarioCribado.CAMPOS_SINTOMAS
        if getattr(cribado, campo)
    ]
    hallazgos = ', '.join(positivos) if positivos else 'sin sintomas positivos registrados'
    return (
        f'Cribado FACCI con {cribado.get_nivel_riesgo_display()} y puntaje '
        f'{cribado.puntaje_total}/{len(CuestionarioCribado.CAMPOS_SINTOMAS)}. '
        f'Hallazgos positivos: {hallazgos}.'
    )


def _ultimo_cribado_del_paciente(paciente):
    return (
        CuestionarioCribado.objects
        .filter(paciente=paciente)
        .select_related('paciente', 'medico')
        .order_by('-fecha_evaluacion', '-created_at')
        .first()
    )


@login_required
@requiere_acceso('puede_ver_referencias')
def lista_view(request):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        referencias = ReferenciaMedica.objects.filter(
            Q(medico_referente=request.user) |
            Q(paciente__medico_asignado=request.user) |
            Q(paciente__creado_por=request.user)
        ).distinct()
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        referencias = ReferenciaMedica.objects.filter(
            Q(especialista_destino=request.user) | Q(medico_referente=request.user)
        ).distinct()
    elif request.user.rol == CustomUser.Rol.ENFERMERA:
        # ENFERMERA: solo referencias de sus pacientes asignados (lectura)
        referencias = ReferenciaMedica.objects.filter(
            Q(paciente__medico_asignado=request.user) | Q(paciente__creado_por=request.user)
        ).distinct()
    else:
        # ADMIN, PERSONAL_FACCI, TRABAJADORA_SOCIAL — visión global para coordinación
        referencias = ReferenciaMedica.objects.all()

    referencias = referencias.select_related(
        'paciente',
        'medico_referente',
        'especialista_destino',
    ).prefetch_related('ingresos_casa_facci')
    search_query = request.GET.get('q', '').strip()
    if search_query:
        referencias = referencias.filter(
            Q(paciente__nombres__icontains=search_query) |
            Q(paciente__apellidos__icontains=search_query) |
            Q(paciente__codigo_paciente__icontains=search_query) |
            Q(hospital_destino__nombre__icontains=search_query) |
            Q(motivo_referencia__icontains=search_query) |
            Q(medico_referente__first_name__icontains=search_query) |
            Q(medico_referente__last_name__icontains=search_query) |
            Q(especialista_destino__first_name__icontains=search_query) |
            Q(especialista_destino__last_name__icontains=search_query)
        )

    urgentes_sin_asignar = []
    if request.user.rol in [CustomUser.Rol.ADMIN, CustomUser.Rol.ONCOLOGO]:
        urgentes_sin_asignar = list(
            ReferenciaMedica.objects.filter(
                especialista_destino__isnull=True,
                estado=ReferenciaMedica.EstadoReferencia.PENDIENTE,
                prioridad=ReferenciaMedica.Prioridad.URGENTE,
            ).select_related('paciente').order_by('created_at')
        )

    # ── Paneles del especialista destino (estilo Casa FACCI) ──────────
    # Referencias que este usuario, como especialista destino, debe aceptar,
    # y las que ya aceptó/están en proceso y aún puede contrarreferir.
    mis_por_aceptar = []
    mis_por_contrarreferir = []
    if request.user.rol in [
        CustomUser.Rol.ONCOLOGO, CustomUser.Rol.PEDIATRA,
        CustomUser.Rol.MEDICO, CustomUser.Rol.ADMIN,
    ]:
        base_destino = ReferenciaMedica.objects.filter(
            especialista_destino=request.user
        ).select_related('paciente', 'medico_referente')
        mis_por_aceptar = list(
            base_destino.filter(estado=ReferenciaMedica.EstadoReferencia.PENDIENTE)
            .order_by('fecha_referencia')
        )
        mis_por_contrarreferir = list(
            base_destino.filter(
                estado__in=[
                    ReferenciaMedica.EstadoReferencia.ACEPTADA,
                    ReferenciaMedica.EstadoReferencia.EN_PROCESO,
                ],
                contrarreferencia__isnull=True,
            ).order_by('fecha_referencia')
        )

    total = referencias.count()
    en_transito = referencias.filter(estado=ReferenciaMedica.EstadoReferencia.EN_PROCESO).count()
    pendientes = referencias.filter(estado=ReferenciaMedica.EstadoReferencia.PENDIENTE).count()
    aceptadas = referencias.filter(estado=ReferenciaMedica.EstadoReferencia.ACEPTADA).count()
    paginator = Paginator(referencias.order_by('-fecha_referencia'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'titulo_pagina': 'Referencias Medicas',
        'referencias': page_obj,
        'page_obj': page_obj,
        'total': total,
        'en_transito': en_transito,
        'pendientes': pendientes,
        'aceptadas': aceptadas,
        'urgentes_sin_asignar': urgentes_sin_asignar,
        'mis_por_aceptar': mis_por_aceptar,
        'mis_por_contrarreferir': mis_por_contrarreferir,
        'filtro_search': search_query,
    }
    return render(request, 'referencias/lista.html', context)


def _responsable_desde_paciente(paciente):
    tutor = getattr(paciente, 'padre_tutor', None)
    user = getattr(tutor, 'usuario', None) if tutor else None
    return {
        'nombre': user.get_full_name() if user else '',
        'parentesco': tutor.get_parentesco_display() if tutor else '',
        'cedula': getattr(user, 'cedula', '') or '',
        'telefono': getattr(tutor, 'telefono_emergencia', '') if tutor else '',
        'celular': getattr(user, 'telefono', '') or '',
        'direccion': getattr(tutor, 'direccion', '') if tutor else '',
        'ocupacion': getattr(tutor, 'ocupacion', '') if tutor else '',
    }


def _responsable_vacio():
    return {
        'nombre': '',
        'parentesco': '',
        'cedula': '',
        'telefono': '',
        'celular': '',
        'direccion': '',
        'ocupacion': '',
    }


def _ingreso_activo_existe(paciente):
    estados_activos = [
        ReferenciaIngresoCasaFACCI.Estado.PENDIENTE,
        ReferenciaIngresoCasaFACCI.Estado.APROBADA,
        ReferenciaIngresoCasaFACCI.Estado.INGRESADO,
    ]
    return ReferenciaIngresoCasaFACCI.objects.filter(
        paciente=paciente,
        estado__in=estados_activos,
    ).exists()


def _habitaciones_disponibles():
    return HabitacionCasa.objects.filter(activa=True).order_by('nombre')


@login_required
@requiere_acceso('puede_ver_referencias')
def historial_paciente(request, paciente_id):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    paciente = get_object_or_404(Paciente.objects.select_related('padre_tutor__usuario'), pk=paciente_id)
    if not _usuario_puede_ver_paciente(request.user, paciente):
        messages.error(request, 'No tiene permiso para ver el historial de referencias de este paciente.')
        return redirect('referencias:lista')

    referencias = ReferenciaMedica.objects.filter(paciente=paciente).select_related(
        'medico_referente',
        'especialista_destino',
    ).order_by('-fecha_referencia')
    ingresos_casa = ReferenciaIngresoCasaFACCI.objects.filter(paciente=paciente).select_related(
        'referencia_medica',
        'habitacion',
        'creado_por',
    ).order_by('-fecha_creacion')

    context = {
        'paciente': paciente,
        'referencias': referencias,
        'ingresos_casa': ingresos_casa,
    }
    return render(request, 'referencias/historial_paciente.html', context)


def _contexto_crear_ingreso(request, referencia=None, paciente=None, form_data=None):
    responsable = _responsable_desde_paciente(paciente) if paciente else _responsable_vacio()
    return {
        'referencia': referencia,
        'paciente_preseleccionado': paciente,
        'pacientes': _pacientes_queryset_para_usuario(request.user).order_by('nombres', 'apellidos'),
        'habitaciones': _habitaciones_disponibles(),
        'estados': ReferenciaIngresoCasaFACCI.Estado.choices,
        'hoy': timezone.localdate().isoformat(),
        'responsable': responsable,
        'form_data': form_data or {},
        'centros': CentroSalud.objects.filter(activo=True).order_by('nombre'),
        'casa_facci': CentroSalud.objects.filter(nombre__iexact='Casa FACCI').first(),
    }


@login_required
def crear_ingreso_casa_facci(request, pk=None):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    referencia = None
    paciente_preseleccionado = None
    if pk:
        try:
            uuid.UUID(str(pk))
        except (ValueError, AttributeError):
            raise Http404('Referencia no encontrada.')
        referencia = get_object_or_404(
            ReferenciaMedica.objects.select_related('paciente__padre_tutor__usuario', 'medico_referente', 'especialista_destino'),
            pk=pk,
        )
        paciente_preseleccionado = referencia.paciente
        if not _usuario_puede_ver_paciente(request.user, paciente_preseleccionado):
            messages.error(request, 'No tiene permiso para referir este paciente a Casa FACCI.')
            return redirect('referencias:lista')
    elif request.GET.get('paciente'):
        paciente_preseleccionado = get_object_or_404(Paciente.objects.select_related('padre_tutor__usuario'), pk=request.GET['paciente'])
        if not _usuario_puede_ver_paciente(request.user, paciente_preseleccionado):
            messages.error(request, 'No tiene permiso para referir este paciente a Casa FACCI.')
            return redirect('referencias:lista')

    if request.method == 'POST':
        form_data = request.POST
        paciente = paciente_preseleccionado
        if not paciente:
            paciente_id = request.POST.get('paciente', '').strip()
            if paciente_id:
                paciente = _pacientes_queryset_para_usuario(request.user).filter(pk=paciente_id).first()

        habitacion = None
        habitacion_id = request.POST.get('habitacion', '').strip()
        if habitacion_id:
            habitacion = HabitacionCasa.objects.filter(pk=habitacion_id, activa=True).first()

        centro_origen_id = request.POST.get('centro_origen', '').strip()
        hospital_destino_id = request.POST.get('hospital_destino', '').strip()

        fecha_entrada = parse_date(request.POST.get('fecha_entrada', '') or '')
        fecha_salida = parse_date(request.POST.get('fecha_salida', '') or '')
        motivo_ingreso = request.POST.get('motivo_ingreso', '').strip()
        estado = request.POST.get('estado') or ReferenciaIngresoCasaFACCI.Estado.PENDIENTE

        errors = []
        if not paciente:
            errors.append('Seleccione un paciente valido.')
        if not motivo_ingreso:
            errors.append('El motivo de ingreso es obligatorio.')
        if not fecha_entrada:
            errors.append('La fecha de entrada es obligatoria.')
        if fecha_entrada and fecha_salida and fecha_salida < fecha_entrada:
            errors.append('La fecha de salida no puede ser menor que la fecha de entrada.')
        if estado not in ReferenciaIngresoCasaFACCI.Estado.values:
            estado = ReferenciaIngresoCasaFACCI.Estado.PENDIENTE
        if habitacion_id and not habitacion:
            errors.append('Habitacion no encontrada o no habilitada.')
        if habitacion and not habitacion.disponible:
            errors.append(f'La habitacion "{habitacion.nombre}" no tiene cupo disponible.')
        if paciente and _ingreso_activo_existe(paciente):
            errors.append(f'{paciente.nombre_completo} ya tiene una referencia activa de ingreso Casa FACCI.')
        if paciente and EstanciaFamiliar.objects.filter(paciente=paciente, estado=EstanciaFamiliar.Estado.ACTIVA).exists():
            errors.append(f'{paciente.nombre_completo} ya tiene una estancia activa en Casa FACCI.')

        if errors:
            for error in errors:
                messages.error(request, error)
            context = _contexto_crear_ingreso(request, referencia, paciente, form_data)
            return render(request, 'referencias/crear_ingreso_casa_facci.html', context)

        responsable = _responsable_desde_paciente(paciente)
        ingreso = ReferenciaIngresoCasaFACCI.objects.create(
            paciente=paciente,
            referencia_medica=referencia,
            centro_origen=(
                (CentroSalud.objects.filter(pk=centro_origen_id).first() if centro_origen_id else None)
                or getattr(request.user, 'centro_medico', None)
                or (referencia.medico_referente.centro_medico if referencia else None)
            ),
            hospital_destino=(
                (CentroSalud.objects.filter(pk=hospital_destino_id).first() if hospital_destino_id else None)
                or CentroSalud.objects.filter(nombre__iexact='Casa FACCI').first()
            ),
            motivo_ingreso=motivo_ingreso,
            fecha_entrada=fecha_entrada,
            fecha_salida=fecha_salida,
            tiempo_estadia=request.POST.get('tiempo_estadia', '').strip(),
            habitacion=habitacion,
            responsable_paciente=request.POST.get('responsable_paciente', '').strip() or responsable.get('nombre', ''),
            parentesco_responsable=request.POST.get('parentesco_responsable', '').strip() or responsable.get('parentesco', ''),
            cedula_responsable=request.POST.get('cedula_responsable', '').strip() or responsable.get('cedula', ''),
            telefono_responsable=request.POST.get('telefono_responsable', '').strip() or responsable.get('telefono', ''),
            celular_responsable=request.POST.get('celular_responsable', '').strip() or responsable.get('celular', ''),
            direccion_responsable=request.POST.get('direccion_responsable', '').strip() or responsable.get('direccion', ''),
            ocupacion_responsable=request.POST.get('ocupacion_responsable', '').strip() or responsable.get('ocupacion', ''),
            estado=estado,
            observaciones=request.POST.get('observaciones', '').strip(),
            creado_por=request.user,
        )
        registrar_actividad(
            usuario=request.user,
            accion='Crear Ingreso Casa FACCI',
            modelo='ReferenciaIngresoCasaFACCI',
            objeto_id=str(ingreso.id),
            objeto_repr=str(ingreso),
            descripcion=f'Referencia de ingreso Casa FACCI creada para {paciente.nombre_completo}.',
        )
        messages.success(request, 'Referencia de ingreso Casa FACCI creada correctamente.')
        return redirect('referencias:formulario_ingreso_casa_facci', pk=ingreso.pk)

    context = _contexto_crear_ingreso(request, referencia, paciente_preseleccionado)
    return render(request, 'referencias/crear_ingreso_casa_facci.html', context)


def _ingreso_queryset():
    return ReferenciaIngresoCasaFACCI.objects.select_related(
        'paciente__padre_tutor__usuario',
        'referencia_medica__medico_referente',
        'referencia_medica__especialista_destino',
        'habitacion',
        'creado_por',
    )


@login_required
def formulario_ingreso_casa_facci(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    ingreso = get_object_or_404(_ingreso_queryset(), pk=pk)
    if not _usuario_puede_ver_ingreso(request.user, ingreso):
        messages.error(request, 'No tiene permiso para ver este formulario.')
        return redirect('referencias:lista')

    context = build_ingreso_casa_context(ingreso)
    context['auto_print'] = request.GET.get('print') == '1'
    return render(request, 'referencias/formulario_ingreso_casa_facci.html', context)


@login_required
def formulario_ingreso_casa_facci_pdf(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    ingreso = get_object_or_404(_ingreso_queryset(), pk=pk)
    if not _usuario_puede_ver_ingreso(request.user, ingreso):
        messages.error(request, 'No tiene permiso para descargar este formulario.')
        return redirect('referencias:lista')

    context = build_ingreso_casa_context(ingreso)
    response = HttpResponse(render_ingreso_casa_pdf(context), content_type='application/pdf')
    # `inline` permite abrir el PDF en el visor del navegador para imprimirlo
    # (queda perfecto en Letter 8.5x11); por defecto se descarga como adjunto.
    disposition = 'inline' if request.GET.get('inline') == '1' else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{ingreso_pdf_filename(ingreso)}"'
    return response


@login_required
@requiere_acceso('puede_gestionar_referencias')
def crear_view(request):
    if request.user.rol not in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO, CustomUser.Rol.ONCOLOGO, CustomUser.Rol.ADMIN]:
        messages.error(request, 'Su rol no tiene autorización para generar referencias médicas.')
        return redirect('referencias:lista')

    cribado = None
    paciente_preseleccionado = None
    cribado_id = request.POST.get('cribado_id') or request.GET.get('cribado')
    paciente_id = request.POST.get('paciente') or request.GET.get('paciente')

    if cribado_id:
        cribado = get_object_or_404(
            CuestionarioCribado.objects.select_related('paciente', 'medico'),
            pk=cribado_id,
        )
        if ReferenciaMedica.objects.filter(cuestionario=cribado).exists():
            messages.warning(request, 'Advertencia: El cribado seleccionado ya tiene una referencia médica asociada.')
            return redirect('referencias:lista')

        if paciente_id and str(cribado.paciente_id) != str(paciente_id):
            messages.error(request, 'El cribado seleccionado no pertenece al paciente indicado.')
            return redirect('referencias:crear')
        paciente_preseleccionado = cribado.paciente
    elif paciente_id:
        paciente_preseleccionado = get_object_or_404(Paciente, pk=paciente_id)
        cribado = _ultimo_cribado_del_paciente(paciente_preseleccionado)
        if cribado and ReferenciaMedica.objects.filter(cuestionario=cribado).exists():
            cribado = None

    if paciente_preseleccionado:
        is_authorized = (
            request.user.rol in [CustomUser.Rol.ADMIN, CustomUser.Rol.ONCOLOGO] or
            paciente_preseleccionado.medico_asignado == request.user or
            paciente_preseleccionado.creado_por == request.user or
            (cribado and cribado.medico == request.user)
        )
        if not is_authorized:
            messages.error(request, 'No tiene permiso para crear referencias para este paciente.')
            return redirect('referencias:lista')

    if request.method == 'POST':
        paciente = paciente_preseleccionado
        if not paciente:
            messages.error(request, 'Seleccione un paciente valido para crear la referencia.')
            return redirect('referencias:crear')

        hospital_destino_id = request.POST.get('hospital_destino', '').strip()
        motivo_referencia = request.POST.get('motivo_referencia', '').strip()
        prioridad = request.POST.get('prioridad') or ReferenciaMedica.Prioridad.MEDIA
        especialista_id = request.POST.get('especialista_destino') or None

        hospital_destino = CentroSalud.objects.filter(pk=hospital_destino_id).first() if hospital_destino_id else None
        if not hospital_destino or not motivo_referencia:
            messages.error(request, 'Complete hospital destino y motivo clinico de la referencia.')
            return redirect(request.get_full_path())
        if prioridad not in ReferenciaMedica.Prioridad.values:
            prioridad = ReferenciaMedica.Prioridad.MEDIA

        especialista = None
        if especialista_id:
            especialista = _especialistas_queryset(excluir_usuario=request.user).filter(pk=especialista_id).first()

        with transaction.atomic():
            referencia = ReferenciaMedica.objects.create(
                paciente=paciente,
                cuestionario=cribado,
                medico_referente=request.user,
                especialista_destino=especialista,
                hospital_destino=hospital_destino,
                motivo_referencia=motivo_referencia,
                prioridad=prioridad,
                fecha_cita=_parse_fecha_cita(request.POST.get('fecha_cita', '').strip()),
                observaciones=request.POST.get('observaciones', '').strip(),
            )
            paciente.estado_actual = Paciente.EstadoPaciente.REFERIDO
            paciente.save(update_fields=['estado_actual', 'updated_at'])
            registrar_actividad(
                usuario=request.user,
                accion='Crear Referencia Medica',
                modelo='ReferenciaMedica',
                objeto_id=str(referencia.id),
                objeto_repr=str(referencia),
                descripcion=f'Referencia creada para {paciente.nombre_completo} hacia {hospital_destino}.',
            )

        messages.success(request, 'Referencia medica creada correctamente.')
        return redirect('referencias:detalle', pk=referencia.pk)

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

    pacientes = list(
        pacientes_qs.order_by('nombres', 'apellidos').prefetch_related(
            Prefetch(
                'cribados',
                queryset=CuestionarioCribado.objects.order_by('-fecha_evaluacion', '-created_at'),
                to_attr='cribados_para_referencia',
            )
        )
    )
    for paciente in pacientes:
        paciente.cribado_reciente = (
            paciente.cribados_para_referencia[0]
            if paciente.cribados_para_referencia
            else None
        )

    context = {
        'titulo_pagina': 'Nueva Referencia Medica',
        'hospitales': CentroSalud.objects.filter(activo=True).order_by('nombre'),
        'especialidades': _get_especialidades(),
        'prioridades': ReferenciaMedica.Prioridad.choices,
        'pacientes': pacientes,
        'especialistas': _especialistas_queryset(excluir_usuario=request.user),
        'cribado': cribado,
        'paciente_preseleccionado': paciente_preseleccionado,
        'motivo_sugerido': _motivo_desde_cribado(cribado) if cribado else '',
        'score_maximo': len(CuestionarioCribado.CAMPOS_SINTOMAS),
    }
    return render(request, 'referencias/crear.html', context)


@login_required
@requiere_acceso('puede_ver_referencias')
def detalle_view(request, pk):
    try:
        uuid.UUID(str(pk))
    except (ValueError, AttributeError):
        raise Http404('Referencia no encontrada.')

    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    referencia = get_object_or_404(
        ReferenciaMedica.objects.select_related('paciente', 'medico_referente', 'especialista_destino'),
        pk=pk,
    )

    es_referente = (
        referencia.medico_referente == request.user or
        referencia.paciente.medico_asignado == request.user or
        referencia.paciente.creado_por == request.user
    )
    es_destinatario = referencia.especialista_destino == request.user

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        if not (es_referente or es_destinatario):
            messages.error(request, 'No tiene permiso para ver esta referencia médica.')
            return redirect('referencias:lista')
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        es_urgente_sin_asignar = (
            referencia.especialista_destino_id is None and
            referencia.estado == ReferenciaMedica.EstadoReferencia.PENDIENTE and
            referencia.prioridad == ReferenciaMedica.Prioridad.URGENTE
        )
        if not (es_destinatario or referencia.medico_referente == request.user or es_urgente_sin_asignar):
            messages.error(request, 'No tiene permiso para ver esta referencia médica.')
            return redirect('referencias:lista')

    ER = ReferenciaMedica.EstadoReferencia

    # Transiciones permitidas según rol
    TRANSICIONES_DESTINATARIO = {
        ER.PENDIENTE:  [(ER.ACEPTADA, 'Aceptar referencia', 'check_circle', 'primary'),
                        (ER.CANCELADA, 'Rechazar referencia', 'cancel', 'error')],
        ER.ACEPTADA:   [(ER.EN_PROCESO, 'Iniciar atención', 'play_circle', 'primary'),
                        (ER.CANCELADA, 'Cancelar', 'cancel', 'error')],
        ER.EN_PROCESO: [(ER.COMPLETADA, 'Marcar completada', 'task_alt', 'primary'),
                        (ER.CANCELADA, 'Cancelar', 'cancel', 'error')],
    }
    TRANSICIONES_REFERENTE = {
        ER.PENDIENTE:  [(ER.CANCELADA, 'Cancelar referencia', 'cancel', 'error')],
        ER.ACEPTADA:   [(ER.CANCELADA, 'Cancelar referencia', 'cancel', 'error')],
    }

    if request.method == 'POST':
        nuevo_estado = (request.POST.get('nuevo_estado') or request.POST.get('estado') or '').strip()
        nota = request.POST.get('nota', '').strip()

        transiciones_validas = []
        if es_destinatario:
            transiciones_validas += [t[0] for t in TRANSICIONES_DESTINATARIO.get(referencia.estado, [])]
        if es_referente:
            transiciones_validas += [t[0] for t in TRANSICIONES_REFERENTE.get(referencia.estado, [])]

        if nuevo_estado not in transiciones_validas:
            messages.error(request, 'Transición de estado no permitida.')
            return redirect('referencias:detalle', pk=pk)

        if nuevo_estado == ER.COMPLETADA and not nota and not getattr(referencia, 'contrarreferencia', None):
            messages.error(request, 'Debe ingresar al menos una observación de resultado para marcar la referencia como atendida/completada.')
            return redirect('referencias:detalle', pk=pk)

        estado_anterior = referencia.get_estado_display()
        referencia.estado = nuevo_estado
        referencia.save(update_fields=['estado', 'updated_at'])

        registrar_actividad(
            usuario=request.user,
            accion='Cambio de estado — Referencia',
            modelo='ReferenciaMedica',
            objeto_id=str(referencia.id),
            objeto_repr=str(referencia),
            descripcion=f'{estado_anterior} → {referencia.get_estado_display()}. {nota}' if nota else f'{estado_anterior} → {referencia.get_estado_display()}.',
        )
        messages.success(request, f'Estado actualizado a: {referencia.get_estado_display()}.')
        return redirect('referencias:detalle', pk=pk)

    # Construir historial desde LogActividad
    logs = LogActividad.objects.filter(
        modelo='ReferenciaMedica', objeto_id=str(referencia.id)
    ).select_related('usuario').order_by('fecha')

    historial = [{
        'label': 'Creada',
        'fecha': referencia.fecha_referencia,
        'usuario': referencia.medico_origen,
        'nota': 'Generada desde cribado positivo.' if referencia.cuestionario else 'Generada manualmente.',
        'icono': 'add_circle',
        'color': 'primary',
    }]
    for log in logs:
        historial.append({
            'label': log.accion,
            'fecha': log.fecha,
            'usuario': log.usuario.get_full_name() if log.usuario else 'Sistema',
            'nota': log.descripcion,
            'icono': 'update',
            'color': 'secondary',
        })

    acciones_disponibles = []
    if es_destinatario:
        acciones_disponibles += TRANSICIONES_DESTINATARIO.get(referencia.estado, [])
    if es_referente and not es_destinatario:
        acciones_disponibles += TRANSICIONES_REFERENTE.get(referencia.estado, [])

    contrarreferencia = getattr(referencia, 'contrarreferencia', None)
    ingreso_casa = referencia.ingresos_casa_facci.select_related('habitacion').order_by('-fecha_creacion').first()

    context = {
        'titulo_pagina': referencia.codigo,
        'referencia': referencia,
        'historial': historial,
        'acciones': acciones_disponibles,
        'es_destinatario': es_destinatario,
        'es_referente': es_referente,
        'contrarreferencia': contrarreferencia,
        'ingreso_casa': ingreso_casa,
        'puede_contrarreferir': (
            es_destinatario and
            contrarreferencia is None and
            referencia.estado in [
                ReferenciaMedica.EstadoReferencia.ACEPTADA,
                ReferenciaMedica.EstadoReferencia.EN_PROCESO,
                ReferenciaMedica.EstadoReferencia.COMPLETADA,
            ]
        ),
    }
    return render(request, 'referencias/detalle.html', context)


@login_required
@requiere_acceso('puede_ver_referencias')
def imprimir_view(request, pk):
    try:
        uuid.UUID(str(pk))
    except (ValueError, AttributeError):
        raise Http404('Referencia no encontrada.')

    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    referencia = get_object_or_404(
        ReferenciaMedica.objects.select_related(
            'paciente', 'medico_referente', 'especialista_destino', 'cuestionario'
        ),
        pk=pk,
    )

    paciente = referencia.paciente
    ultimo_seguimiento = (
        paciente.seguimientos
        .select_related('medico')
        .order_by('-fecha_seguimiento')
        .first()
    )
    ultimo_cribado = (
        paciente.cribados
        .order_by('-fecha_evaluacion')
        .first()
    )

    context = {
        'referencia': referencia,
        'paciente': paciente,
        'ultimo_seguimiento': ultimo_seguimiento,
        'ultimo_cribado': ultimo_cribado,
        'fecha_impresion': timezone.now().date(),
    }
    return render(request, 'referencias/imprimir.html', context)


@login_required
@requiere_acceso('puede_gestionar_referencias')
def contrarreferencia_crear_view(request, ref_pk):
    try:
        uuid.UUID(str(ref_pk))
    except (ValueError, AttributeError):
        raise Http404('Referencia no encontrada.')

    referencia = get_object_or_404(
        ReferenciaMedica.objects.select_related('paciente', 'medico_referente', 'especialista_destino'),
        pk=ref_pk,
    )

    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    es_destinatario = referencia.especialista_destino == request.user
    es_admin = request.user.rol == CustomUser.Rol.ADMIN

    if not (es_destinatario or es_admin):
        messages.error(request, 'Solo el especialista destino puede emitir la contrarreferencia.')
        return redirect('referencias:detalle', pk=ref_pk)

    if referencia.tiene_contrarreferencia:
        messages.info(request, 'Esta referencia ya tiene una contrarreferencia emitida.')
        return redirect('referencias:contrarreferencia_detalle', pk=referencia.contrarreferencia.pk)

    estados_validos = [
        ReferenciaMedica.EstadoReferencia.ACEPTADA,
        ReferenciaMedica.EstadoReferencia.EN_PROCESO,
        ReferenciaMedica.EstadoReferencia.COMPLETADA,
    ]
    if referencia.estado not in estados_validos:
        messages.error(request, 'La referencia debe estar aceptada o en proceso para emitir contrarreferencia.')
        return redirect('referencias:detalle', pk=ref_pk)

    if request.method == 'POST':
        fecha_atencion = request.POST.get('fecha_atencion', '').strip()
        diagnostico = request.POST.get('diagnostico', '').strip()
        tipo_cancer = request.POST.get('tipo_cancer', '').strip()
        estadio = request.POST.get('estadio', Contrarreferencia.Estadio.NE)
        tratamiento_realizado = request.POST.get('tratamiento_realizado', '').strip()
        estudios_realizados = request.POST.get('estudios_realizados', '').strip()
        medicamentos_indicados = request.POST.get('medicamentos_indicados', '').strip()
        resultado_atencion = request.POST.get('resultado_atencion', '').strip()
        recomendaciones = request.POST.get('recomendaciones', '').strip()
        requiere_seguimiento_raw = request.POST.get('requiere_seguimiento_facci')
        requiere_seguimiento = str(requiere_seguimiento_raw).lower() in {'on', 'true', '1', 'yes', 'si', 'sí'}
        proxima_cita_raw = request.POST.get('proxima_cita', '').strip()

        if not fecha_atencion or not diagnostico or not resultado_atencion:
            messages.error(request, 'Fecha de atención, diagnóstico y resultado son obligatorios.')
            return redirect(request.get_full_path())

        if resultado_atencion not in Contrarreferencia.ResultadoAtencion.values:
            messages.error(request, 'Resultado de atención no válido.')
            return redirect(request.get_full_path())

        proxima_cita = None
        if proxima_cita_raw:
            proxima_cita = parse_date(proxima_cita_raw)

        with transaction.atomic():
            contra = Contrarreferencia.objects.create(
                referencia=referencia,
                medico_contrarreferente=request.user,
                fecha_atencion=fecha_atencion,
                diagnostico=diagnostico,
                tipo_cancer=tipo_cancer if tipo_cancer in Contrarreferencia.TipoCancer.values else '',
                estadio=estadio if estadio in Contrarreferencia.Estadio.values else Contrarreferencia.Estadio.NE,
                tratamiento_realizado=tratamiento_realizado,
                estudios_realizados=estudios_realizados,
                medicamentos_indicados=medicamentos_indicados,
                resultado_atencion=resultado_atencion,
                recomendaciones=recomendaciones,
                requiere_seguimiento_facci=requiere_seguimiento,
                proxima_cita=proxima_cita,
            )
            if referencia.estado != ReferenciaMedica.EstadoReferencia.COMPLETADA:
                referencia.estado = ReferenciaMedica.EstadoReferencia.COMPLETADA
                referencia.save(update_fields=['estado', 'updated_at'])

            registrar_actividad(
                usuario=request.user,
                accion='Emitir Contrarreferencia',
                modelo='Contrarreferencia',
                objeto_id=str(contra.id),
                objeto_repr=str(contra),
                descripcion=f'Contrarreferencia emitida para {referencia.paciente.nombre_completo}. Resultado: {contra.get_resultado_atencion_display()}.',
            )

        messages.success(request, 'Contrarreferencia emitida correctamente.')
        return redirect('referencias:contrarreferencia_detalle', pk=contra.pk)

    context = {
        'titulo_pagina': f'Contrarreferencia — {referencia.codigo}',
        'referencia': referencia,
        'tipos_cancer': Contrarreferencia.TipoCancer.choices,
        'estadios': Contrarreferencia.Estadio.choices,
        'resultados': Contrarreferencia.ResultadoAtencion.choices,
        'hoy': timezone.now().date().isoformat(),
    }
    return render(request, 'referencias/contrarreferencia_crear.html', context)


@login_required
@requiere_acceso('puede_ver_referencias')
def contrarreferencia_detalle_view(request, pk):
    try:
        uuid.UUID(str(pk))
    except (ValueError, AttributeError):
        raise Http404('Contrarreferencia no encontrada.')

    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    contra = get_object_or_404(
        Contrarreferencia.objects.select_related(
            'referencia__paciente',
            'referencia__medico_referente',
            'referencia__especialista_destino',
            'medico_contrarreferente',
        ),
        pk=pk,
    )

    referencia = contra.referencia
    es_referente = (
        referencia.medico_referente == request.user or
        referencia.paciente.medico_asignado == request.user or
        referencia.paciente.creado_por == request.user
    )
    es_destinatario = referencia.especialista_destino == request.user

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        if not (es_referente or es_destinatario):
            messages.error(request, 'No tiene permiso para ver esta contrarreferencia.')
            return redirect('referencias:lista')
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        if not (es_destinatario or referencia.medico_referente == request.user):
            messages.error(request, 'No tiene permiso para ver esta contrarreferencia.')
            return redirect('referencias:lista')

    context = {
        'titulo_pagina': contra.codigo,
        'contra': contra,
        'referencia': referencia,
        'es_referente': es_referente,
        'es_destinatario': es_destinatario,
    }
    return render(request, 'referencias/contrarreferencia_detalle.html', context)


@login_required
@requiere_acceso('puede_subir_documentos')
def guardar_documento_msp_view(request, pk):
    if request.method != 'POST':
        return redirect('referencias:imprimir', pk=pk)

    try:
        uuid.UUID(str(pk))
    except (ValueError, AttributeError):
        raise Http404('Referencia no encontrada.')

    referencia = get_object_or_404(ReferenciaMedica, pk=pk)

    if not _usuario_puede_ver_paciente(request.user, referencia.paciente):
        messages.error(request, 'No tiene permiso para guardar documentos de este paciente.')
        return redirect('referencias:detalle', pk=pk)

    # Recoger parámetros del POST
    post_data = {
        'establecimiento_refiere': request.POST.get('establecimiento_refiere', '').strip(),
        'ta': request.POST.get('ta', '').strip(),
        'fc': request.POST.get('fc', '').strip(),
        'fr': request.POST.get('fr', '').strip(),
        'temperatura': request.POST.get('temperatura', '').strip(),
        'contra_fecha': request.POST.get('contra_fecha', '').strip(),
        'contra_historia': request.POST.get('contra_historia', '').strip(),
        'contra_medicamentos': request.POST.get('contra_medicamentos', '').strip(),
        'contra_estudios': request.POST.get('contra_estudios', '').strip(),
        'contra_medico': request.POST.get('contra_medico', '').strip(),
        # Nuevos campos de casillas de verificación editables
        'sexo_m': request.POST.get('sexo_m') == '1',
        'sexo_f': request.POST.get('sexo_f') == '1',
        'nacionalidad_dom': request.POST.get('nacionalidad_dom') == '1',
        'nacionalidad_ext': request.POST.get('nacionalidad_ext') == '1',
        'nacionalidad_especifique': request.POST.get('nacionalidad_especifique', '').strip(),
        'ars_nombre': request.POST.get('ars_nombre', '').strip(),
        'ars_cont': request.POST.get('ars_cont') == '1',
        'ars_subs': request.POST.get('ars_subs') == '1',
        'ars_otro': request.POST.get('ars_otro') == '1',
        'sintoma_fiebre': request.POST.get('sintoma_fiebre') == '1',
        'sintoma_masa': request.POST.get('sintoma_masa') == '1',
        'sintoma_moretones': request.POST.get('sintoma_moretones') == '1',
        'sintoma_peso': request.POST.get('sintoma_peso') == '1',
        'sintoma_ojo': request.POST.get('sintoma_ojo') == '1',
        'sintoma_vomitos': request.POST.get('sintoma_vomitos') == '1',
        'sintoma_huesos': request.POST.get('sintoma_huesos') == '1',
        'sintoma_sudoracion': request.POST.get('sintoma_sudoracion') == '1',
        'sintoma_ganglios': request.POST.get('sintoma_ganglios') == '1',
        'sintoma_fatiga': request.POST.get('sintoma_fatiga') == '1',
        'sintoma_otro': request.POST.get('sintoma_otro', '').strip(),
    }


    # Generar el PDF
    from .form_msp_pdf import render_msp_form_pdf
    try:
        pdf_content = render_msp_form_pdf(referencia, post_data)
    except Exception as e:
        messages.error(request, f'Error al generar el PDF del formulario: {e}')
        return redirect('referencias:imprimir', pk=pk)

    # Generar el nombre del archivo
    from django.utils.text import slugify
    slug_name = slugify(referencia.paciente.nombre_completo)
    filename = f"formulario_msp_{slug_name}_{timezone.localdate():%Y%m%d}.pdf"

    # Crear el DocumentoMedico
    from apps.documentos.models import DocumentoMedico
    from django.core.files.base import ContentFile
    try:
        with transaction.atomic():
            doc = DocumentoMedico.objects.create(
                paciente=referencia.paciente,
                subido_por=request.user,
                tipo_documento=DocumentoMedico.TipoDocumento.REFERIMIENTO,
                fecha_documento=timezone.localdate(),
                descripcion=f"Formulario de Referencia y Contrarreferencia MSP oficial ({referencia.codigo}).",
                estado=DocumentoMedico.EstadoDocumento.REVISADO
            )
            doc.archivo.save(filename, ContentFile(pdf_content), save=True)

            registrar_actividad(
                usuario=request.user,
                accion='Guardar Formulario MSP',
                modelo='DocumentoMedico',
                objeto_id=str(doc.id),
                objeto_repr=str(doc),
                descripcion=f'Formulario de Referencia y Contrarreferencia MSP oficial ({referencia.codigo}) guardado en el expediente de {referencia.paciente.nombre_completo}.',
            )
        messages.success(request, 'El formulario MSP se generó y se guardó correctamente en el expediente del paciente.')
    except Exception as e:
        messages.error(request, f'Error al guardar el documento en el expediente: {e}')
        return redirect('referencias:imprimir', pk=pk)

    return redirect('pacientes:expediente', pk=referencia.paciente.id)

