import csv
from io import StringIO
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.audit import registrar_actividad
from apps.core.decorators import requiere_acceso
from apps.pacientes.models import NotaClinica
from apps.pacientes.models import Paciente
from apps.referencias.models import ReferenciaMedica

from .models import CuestionarioCribado


SECCIONES_CUESTIONARIO = [
    {
        'id': 'general',
        'titulo': 'Sintomas generales',
        'icono': 'thermostat',
        'preguntas': [
            {'campo': 'fiebre_persistente', 'texto': 'Fiebre persistente por mas de 2 semanas sin causa aparente'},
            {'campo': 'perdida_peso', 'texto': 'Perdida de peso inexplicable'},
            {'campo': 'dolor_huesos', 'texto': 'Dolor en huesos o articulaciones'},
            {'campo': 'palidez', 'texto': 'Palidez marcada o aspecto enfermizo persistente'},
            {'campo': 'fatiga', 'texto': 'Fatiga o cansancio extremo inusual para su edad'},
        ],
    },
    {
        'id': 'hematologico',
        'titulo': 'Signos hematologicos',
        'icono': 'bloodtype',
        'preguntas': [
            {'campo': 'moretones', 'texto': 'Moretones o hematomas frecuentes sin traumatismo'},
            {'campo': 'sangrado', 'texto': 'Sangrado espontaneo de encias, nariz u otras zonas'},
            {'campo': 'ganglios', 'texto': 'Ganglios inflamados en cuello, axilas o ingle'},
            {'campo': 'infecciones_recurrentes', 'texto': 'Infecciones recurrentes o de dificil recuperacion'},
        ],
    },
    {
        'id': 'neurologico_masas',
        'titulo': 'Signos neurologicos y masas',
        'icono': 'neurology',
        'preguntas': [
            {
                'campo': 'dolor_cabeza',
                'texto': 'Dolor de cabeza persistente, especialmente al despertar',
                'alarma_mayor': True,
            },
            {
                'campo': 'vomitos',
                'texto': 'Vomitos matutinos sin causa gastrointestinal',
                'alarma_mayor': True,
            },
            {
                'campo': 'masa_abdominal',
                'texto': 'Masa abdominal palpable o abdomen distendido',
                'alarma_mayor': True,
            },
        ],
    },
    {
        'id': 'oftalmologico',
        'titulo': 'Signos oftalmologicos (Retinoblastoma)',
        'icono': 'visibility',
        'preguntas': [
            {
                'campo': 'leucocoria',
                'texto': 'Leucocoria: pupila blanquecina o reflejo rojo ausente en fotografias con flash',
                'alarma_mayor': True,
                'ayuda': 'Conocido como "ojo de gato". Puede notarse en fotos donde un ojo aparece blanco en vez de rojo.',
            },
        ],
    },
]


def _autor_nombre(usuario):
    return usuario.get_full_name() or usuario.username


def _preguntas():
    return [
        pregunta
        for seccion in SECCIONES_CUESTIONARIO
        for pregunta in seccion['preguntas']
    ]


def _sintomas_contexto(cribado):
    return [
        {
            'campo': pregunta['campo'],
            'nombre': pregunta['texto'],
            'presente': getattr(cribado, pregunta['campo']),
            'alarma_mayor': pregunta.get('alarma_mayor', False),
        }
        for pregunta in _preguntas()
    ]


def _secciones_con_estado(cribado):
    return [
        {
            **seccion,
            'preguntas': [
                {
                    **pregunta,
                    'presente': getattr(cribado, pregunta['campo']),
                }
                for pregunta in seccion['preguntas']
            ],
        }
        for seccion in SECCIONES_CUESTIONARIO
    ]


def _proximos_pasos(cribado):
    if cribado.nivel_riesgo == CuestionarioCribado.NivelRiesgo.ALTO:
        return [
            {'paso': '1', 'accion': 'Crear referencia medica a oncologia pediatrica', 'urgencia': 'Inmediata', 'color': 'error'},
            {'paso': '2', 'accion': 'Solicitar hemograma completo y estudios iniciales segun protocolo local', 'urgencia': '24 horas', 'color': 'secondary'},
            {'paso': '3', 'accion': 'Contactar al tutor y documentar signos de alarma en el expediente', 'urgencia': 'Hoy', 'color': 'primary'},
        ]
    if cribado.nivel_riesgo == CuestionarioCribado.NivelRiesgo.MEDIO:
        return [
            {'paso': '1', 'accion': 'Programar reevaluacion clinica cercana', 'urgencia': '2 semanas', 'color': 'secondary'},
            {'paso': '2', 'accion': 'Registrar nota clinica con evolucion de sintomas', 'urgencia': 'Hoy', 'color': 'primary'},
            {'paso': '3', 'accion': 'Indicar al tutor signos que requieren consulta inmediata', 'urgencia': 'Hoy', 'color': 'primary'},
        ]
    return [
        {'paso': '1', 'accion': 'Continuar vigilancia rutinaria', 'urgencia': 'Mensual', 'color': 'primary'},
        {'paso': '2', 'accion': 'Actualizar expediente si aparecen nuevos sintomas', 'urgencia': 'Segun evolucion', 'color': 'primary'},
    ]


def _descripcion_sintomas_positivos(cribado):
    sintomas = [s['nombre'] for s in _sintomas_contexto(cribado) if s['presente']]
    return ', '.join(sintomas) if sintomas else 'Sin sintomas positivos registrados.'


def _registrar_trazabilidad_cribado(cribado, usuario):
    if cribado.nivel_riesgo == CuestionarioCribado.NivelRiesgo.ALTO:
        tipo_nota = NotaClinica.TipoNota.ALERTA
        importante = True
    else:
        tipo_nota = NotaClinica.TipoNota.OBSERVACION
        importante = cribado.nivel_riesgo == CuestionarioCribado.NivelRiesgo.MEDIO

    NotaClinica.objects.create(
        paciente=cribado.paciente,
        autor=usuario,
        tipo=tipo_nota,
        es_importante=importante,
        texto=(
            f'Cribado FACCI registrado con resultado {cribado.get_resultado_display()} '
            f'({cribado.get_nivel_riesgo_display()}). Puntaje: {cribado.puntaje_total}/'
            f'{len(CuestionarioCribado.CAMPOS_SINTOMAS)}. '
            f'Hallazgos positivos: {_descripcion_sintomas_positivos(cribado)}'
        ),
    )

    estados_evaluables = [
        Paciente.EstadoPaciente.SOSPECHOSO,
        Paciente.EstadoPaciente.EN_ESTUDIO,
        Paciente.EstadoPaciente.DESCARTADO,
    ]
    paciente = cribado.paciente
    if paciente.estado_actual in estados_evaluables:
        if cribado.nivel_riesgo == CuestionarioCribado.NivelRiesgo.ALTO:
            nuevo_estado = Paciente.EstadoPaciente.SOSPECHOSO
        elif cribado.nivel_riesgo == CuestionarioCribado.NivelRiesgo.MEDIO:
            nuevo_estado = Paciente.EstadoPaciente.EN_ESTUDIO
        else:
            nuevo_estado = Paciente.EstadoPaciente.DESCARTADO
        paciente.estado_actual = nuevo_estado
        paciente.save(update_fields=['estado_actual', 'updated_at'])

    registrar_actividad(
        usuario=usuario,
        accion='Crear Cribado FACCI',
        modelo='CuestionarioCribado',
        objeto_id=str(cribado.id),
        objeto_repr=str(cribado),
        descripcion=(
            f'Cribado FACCI para {cribado.paciente.nombre_completo}: '
            f'{cribado.get_nivel_riesgo_display()} ({cribado.puntaje_total}/'
            f'{len(CuestionarioCribado.CAMPOS_SINTOMAS)})'
        ),
    )


@login_required
@requiere_acceso('puede_ver_cribado')
def lista_view(request):
    from apps.auth_app.models import CustomUser
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    cribados = (
        CuestionarioCribado.objects
        .select_related('paciente', 'medico')
        .only(
            'id', 'fecha_evaluacion', 'nivel_riesgo', 'resultado', 'requiere_referencia',
            'fiebre_persistente', 'perdida_peso', 'dolor_huesos', 'palidez', 'fatiga',
            'moretones', 'sangrado', 'ganglios', 'infecciones_recurrentes',
            'dolor_cabeza', 'vomitos', 'masa_abdominal', 'leucocoria',
            'tipo_cancer_sospechado',
            'paciente__id', 'paciente__nombres', 'paciente__apellidos',
            'paciente__codigo_paciente', 'medico__id', 'medico__first_name', 'medico__last_name'
        )
        .order_by('-fecha_evaluacion')
    )

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        cribados = cribados.filter(
            Q(paciente__medico_asignado=request.user) | Q(paciente__creado_por=request.user)
        )
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        cribados = cribados.filter(
            paciente__referencias__especialista_destino=request.user
        ).distinct()

    nivel = request.GET.get('nivel')
    if nivel in CuestionarioCribado.NivelRiesgo.values:
        cribados = cribados.filter(nivel_riesgo=nivel)

    tipo = request.GET.get('tipo')
    if tipo in CuestionarioCribado.TipoCancerSospechado.values:
        cribados = cribados.filter(tipo_cancer_sospechado=tipo)

    buscar = request.GET.get('q', '').strip()
    if buscar:
        cribados = cribados.filter(
            Q(paciente__nombres__icontains=buscar)
            | Q(paciente__apellidos__icontains=buscar)
            | Q(paciente__codigo_paciente__icontains=buscar)
        )

    context = {
        'titulo_pagina': 'Cribado de sintomas',
        'cribados': cribados,
        'total': cribados.count(),
        'riesgo_alto': cribados.filter(nivel_riesgo=CuestionarioCribado.NivelRiesgo.ALTO).count(),
        'requieren_referencia': cribados.filter(requiere_referencia=True).count(),
        'niveles': CuestionarioCribado.NivelRiesgo.choices,
        'nivel_actual': nivel,
        'tipos_cancer': CuestionarioCribado.TipoCancerSospechado.choices,
        'tipo_actual': tipo,
        'score_maximo': len(CuestionarioCribado.CAMPOS_SINTOMAS),
        'buscar': buscar,
    }
    return render(request, 'cribado/lista.html', context)


@login_required
@requiere_acceso('puede_hacer_cribado')
def cuestionario_view(request):
    from apps.auth_app.models import CustomUser
    if request.user.rol not in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        messages.error(request, 'Su rol no tiene autorización para realizar cribados clínicos.')
        return redirect('cribado:lista')

    pacientes = Paciente.objects.filter(
        Q(medico_asignado=request.user) | Q(creado_por=request.user)
    ).select_related('medico_asignado').order_by('nombres', 'apellidos')
    paciente_id = request.POST.get('paciente_id') or request.GET.get('paciente')
    paciente_seleccionado = pacientes.filter(id=paciente_id).first() if paciente_id else None

    if request.method == 'POST':
        if not paciente_seleccionado:
            messages.error(request, 'Seleccione un paciente valido antes de guardar el cuestionario clinico.')
            return redirect('cribado:cuestionario')

        datos_sintomas = {
            pregunta['campo']: request.POST.get(pregunta['campo']) == 'si'
            for pregunta in _preguntas()
        }
        tipo_cancer = request.POST.get('tipo_cancer_sospechado', '').strip()
        if tipo_cancer not in CuestionarioCribado.TipoCancerSospechado.values:
            tipo_cancer = ''
        with transaction.atomic():
            cribado = CuestionarioCribado.objects.create(
                paciente=paciente_seleccionado,
                medico=request.user,
                observaciones=request.POST.get('observaciones', '').strip(),
                tipo_cancer_sospechado=tipo_cancer,
                **datos_sintomas,
            )
            _registrar_trazabilidad_cribado(cribado, request.user)
        messages.success(request, 'Cuestionario clinico guardado correctamente.')
        return redirect('cribado:resultado', pk=cribado.pk)

    context = {
        'titulo_pagina': 'Cuestionario Clinico FACCI',
        'secciones': SECCIONES_CUESTIONARIO,
        'pacientes': pacientes,
        'total_preguntas': len(_preguntas()),
        'paciente_seleccionado': paciente_seleccionado,
        'score_maximo': len(CuestionarioCribado.CAMPOS_SINTOMAS),
        'tipos_cancer': CuestionarioCribado.TipoCancerSospechado.choices,
    }
    return render(request, 'cribado/cuestionario.html', context)


@login_required
@requiere_acceso('puede_ver_cribado')
def resultado_view(request, pk):
    from apps.auth_app.models import CustomUser
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    cribado = get_object_or_404(
        CuestionarioCribado.objects.select_related('paciente', 'medico'),
        pk=pk,
    )

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        if cribado.paciente.medico_asignado != request.user and cribado.paciente.creado_por != request.user:
            messages.error(request, 'No tiene permiso para ver este resultado de cribado.')
            return redirect('cribado:lista')
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        if not cribado.paciente.referencias.filter(especialista_destino=request.user).exists():
            messages.error(request, 'No tiene permiso para ver este resultado de cribado, ya que el paciente no le ha sido referido.')
            return redirect('referencias:lista')

    if cribado.nivel_riesgo == CuestionarioCribado.NivelRiesgo.ALTO:
        nivel = 'alto'
        nivel_color = 'error'
        recomendacion = 'Referencia inmediata a oncologia pediatrica'
        icono = 'warning'
    elif cribado.nivel_riesgo == CuestionarioCribado.NivelRiesgo.MEDIO:
        nivel = 'medio'
        nivel_color = 'secondary'
        recomendacion = 'Seguimiento estrecho y reevaluacion en 2 semanas'
        icono = 'info'
    else:
        nivel = 'bajo'
        nivel_color = 'primary'
        recomendacion = 'Continuar vigilancia rutinaria'
        icono = 'check_circle'

    sintomas = _sintomas_contexto(cribado)
    score_maximo = len(CuestionarioCribado.CAMPOS_SINTOMAS)
    gauge_offset = 314 - round((cribado.puntaje_total / score_maximo) * 314)
    context = {
        'titulo_pagina': 'Resultado del Cribado FACCI',
        'cribado': cribado,
        'resultado': {
            'score': cribado.puntaje_total,
            'score_maximo': score_maximo,
            'gauge_offset': gauge_offset,
            'nivel': nivel,
            'nivel_color': nivel_color,
            'recomendacion': recomendacion,
            'icono': icono,
            'fecha': cribado.fecha_evaluacion.strftime('%d %b, %Y'),
            'medico': _autor_nombre(cribado.medico),
            'paciente': f'{cribado.paciente.nombre_completo}, {cribado.paciente.edad}',
        },
        'sintomas_positivos': [s['nombre'] for s in sintomas if s['presente']],
        'proximos_pasos': _proximos_pasos(cribado),
    }
    return render(request, 'cribado/resultado.html', context)


@login_required
@requiere_acceso('puede_ver_cribado')
def detalle_view(request, pk):
    from apps.auth_app.models import CustomUser
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    cribado = get_object_or_404(
        CuestionarioCribado.objects.select_related('paciente__medico_asignado', 'medico'),
        pk=pk,
    )

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        if cribado.paciente.medico_asignado != request.user and cribado.paciente.creado_por != request.user:
            messages.error(request, 'No tiene permiso para ver este detalle de cribado.')
            return redirect('cribado:lista')
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        if not cribado.paciente.referencias.filter(especialista_destino=request.user).exists():
            messages.error(request, 'No tiene permiso para ver este detalle de cribado, ya que el paciente no le ha sido referido.')
            return redirect('referencias:lista')

    sintomas = _sintomas_contexto(cribado)
    sintomas_positivos = [s for s in sintomas if s['presente']]
    context = {
        'titulo_pagina': f'Detalle Cribado - {cribado.paciente.nombre_completo}',
        'cribado': cribado,
        'sintomas': sintomas,
        'sintomas_positivos': sintomas_positivos,
        'score_maximo': len(CuestionarioCribado.CAMPOS_SINTOMAS),
    }
    return render(request, 'cribado/detalle.html', context)


@login_required
@requiere_acceso('puede_ver_cribado')
def editar_view(request, pk):
    from apps.auth_app.models import CustomUser
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    cribado = get_object_or_404(
        CuestionarioCribado.objects.select_related('paciente', 'medico'),
        pk=pk,
    )

    # Control de permisos: solo el médico que lo creó o admin pueden editar
    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        if cribado.medico != request.user:
            messages.error(request, 'Solo el médico que realizó el cribado puede editarlo.')
            return redirect('cribado:detalle', pk=pk)
    elif request.user.rol != CustomUser.Rol.ADMIN:
        messages.error(request, 'No tiene permiso para editar este cribado.')
        return redirect('cribado:lista')

    if request.method == 'POST':
        datos_sintomas_anteriores = {
            campo: getattr(cribado, campo)
            for campo in CuestionarioCribado.CAMPOS_SINTOMAS
        }

        datos_sintomas_nuevos = {
            pregunta['campo']: request.POST.get(pregunta['campo']) == 'si'
            for pregunta in _preguntas()
        }

        tipo_cancer = request.POST.get('tipo_cancer_sospechado', '').strip()
        if tipo_cancer not in CuestionarioCribado.TipoCancerSospechado.values:
            tipo_cancer = ''
        with transaction.atomic():
            for campo, valor in datos_sintomas_nuevos.items():
                setattr(cribado, campo, valor)
            cribado.observaciones = request.POST.get('observaciones', '').strip()
            cribado.tipo_cancer_sospechado = tipo_cancer
            cribado.save()

            cambios = {k: v for k, v in datos_sintomas_nuevos.items() if datos_sintomas_anteriores[k] != v}
            if cambios:
                descripcion_cambios = ', '.join(
                    f'{k}: {datos_sintomas_anteriores[k]} → {cambios[k]}'
                    for k in cambios
                )
                registrar_actividad(
                    usuario=request.user,
                    accion='Editar Cribado FACCI',
                    modelo='CuestionarioCribado',
                    objeto_id=str(cribado.id),
                    objeto_repr=str(cribado),
                    descripcion=f'Cambios realizados: {descripcion_cambios}. Nuevo nivel: {cribado.get_nivel_riesgo_display()}',
                )

        messages.success(request, 'Cribado actualizado correctamente.')
        return redirect('cribado:resultado', pk=cribado.pk)

    context = {
        'titulo_pagina': f'Editar Cribado - {cribado.paciente.nombre_completo}',
        'secciones': _secciones_con_estado(cribado),
        'cribado': cribado,
        'score_maximo': len(CuestionarioCribado.CAMPOS_SINTOMAS),
        'tipos_cancer': CuestionarioCribado.TipoCancerSospechado.choices,
        'es_edicion': True,
    }
    return render(request, 'cribado/editar.html', context)


@login_required
@requiere_acceso('puede_gestionar_referencias')
def crear_referencia_view(request, pk):
    from apps.auth_app.models import CustomUser
    if request.user.rol not in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO, CustomUser.Rol.ONCOLOGO, CustomUser.Rol.ADMIN]:
        messages.error(request, 'Su rol no tiene autorización para generar referencias médicas.')
        return redirect('cribado:lista')

    if request.method != 'POST':
        return redirect('cribado:resultado', pk=pk)

    cribado = get_object_or_404(
        CuestionarioCribado.objects.select_related('paciente', 'medico'),
        pk=pk,
    )

    is_authorized = (
        request.user.rol in [CustomUser.Rol.ADMIN, CustomUser.Rol.ONCOLOGO] or
        cribado.paciente.medico_asignado == request.user or
        cribado.paciente.creado_por == request.user or
        cribado.medico == request.user
    )
    if not is_authorized:
        messages.error(request, 'No tiene permiso para crear referencias para este paciente.')
        return redirect('cribado:lista')

    referencia_existente = cribado.referencias_generadas.order_by('-fecha_referencia').first()
    if referencia_existente:
        messages.info(request, 'Este cribado ya tiene una referencia medica asociada.')
        return redirect('referencias:detalle', pk=referencia_existente.pk)

    prioridad = ReferenciaMedica.Prioridad.URGENTE
    if cribado.nivel_riesgo == CuestionarioCribado.NivelRiesgo.MEDIO:
        prioridad = ReferenciaMedica.Prioridad.ALTA

    hospital_id = request.POST.get('hospital_destino', '').strip()
    from apps.core.models import CentroSalud
    hospital = CentroSalud.objects.filter(pk=hospital_id).first() if hospital_id else None
    if hospital is None:
        hospital = CentroSalud.objects.filter(nombre__iexact='Centro Oncológico Nacional').first() \
            or CentroSalud.objects.filter(activo=True).order_by('nombre').first()
    motivo = request.POST.get('motivo_referencia', '').strip() or (
        f'Cribado FACCI con {cribado.get_nivel_riesgo_display()} y puntaje '
        f'{cribado.puntaje_total}/{len(CuestionarioCribado.CAMPOS_SINTOMAS)}. '
        f'Hallazgos positivos: {_descripcion_sintomas_positivos(cribado)}'
    )

    with transaction.atomic():
        referencia = ReferenciaMedica.objects.create(
            paciente=cribado.paciente,
            cuestionario=cribado,
            medico_referente=request.user,
            hospital_destino=hospital,
            motivo_referencia=motivo,
            prioridad=prioridad,
            observaciones=request.POST.get('observaciones', '').strip(),
        )
        cribado.paciente.estado_actual = Paciente.EstadoPaciente.REFERIDO
        cribado.paciente.save(update_fields=['estado_actual', 'updated_at'])
        registrar_actividad(
            usuario=request.user,
            accion='Crear Referencia desde Cribado',
            modelo='ReferenciaMedica',
            objeto_id=str(referencia.id),
            objeto_repr=str(referencia),
            descripcion=f'Referencia creada desde cribado FACCI para {cribado.paciente.nombre_completo}.',
        )

    messages.success(request, 'Referencia medica creada desde el cribado.')
    return redirect('referencias:detalle', pk=referencia.pk)


@login_required
@requiere_acceso('puede_ver_cribado')
def exportar_csv_view(request):
    from apps.auth_app.models import CustomUser
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    cribados = (
        CuestionarioCribado.objects
        .select_related('paciente', 'medico')
        .order_by('-fecha_evaluacion')
    )

    if request.user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
        cribados = cribados.filter(
            Q(paciente__medico_asignado=request.user) | Q(paciente__creado_por=request.user)
        )
    elif request.user.rol == CustomUser.Rol.ONCOLOGO:
        cribados = cribados.filter(
            paciente__referencias__especialista_destino=request.user
        ).distinct()

    nivel = request.GET.get('nivel')
    if nivel in CuestionarioCribado.NivelRiesgo.values:
        cribados = cribados.filter(nivel_riesgo=nivel)

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    if fecha_inicio:
        cribados = cribados.filter(fecha_evaluacion__gte=fecha_inicio)
    if fecha_fin:
        cribados = cribados.filter(fecha_evaluacion__lte=fecha_fin)

    if not cribados.exists():
        messages.info(request, 'No hay registros de cribado disponibles para exportar con los filtros seleccionados.')
        return redirect('cribado:lista')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="cribados_facci.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Código Paciente',
        'Nombre Paciente',
        'Edad',
        'Médico Evaluador',
        'Fecha Evaluación',
        'Puntaje Total',
        'Nivel Riesgo',
        'Resultado',
        'Requiere Referencia',
        'Leucocoria',
        'Tipo Cáncer Sospechado',
        'Síntomas Presentes',
    ])

    for cribado in cribados:
        sintomas_presentes = ', '.join([
            campo.replace('_', ' ').title()
            for campo in CuestionarioCribado.CAMPOS_SINTOMAS
            if getattr(cribado, campo)
        ])

        writer.writerow([
            cribado.paciente.codigo_paciente,
            cribado.paciente.nombre_completo,
            cribado.paciente.edad,
            cribado.medico.get_full_name(),
            cribado.fecha_evaluacion.strftime('%d/%m/%Y %H:%M'),
            cribado.puntaje_total,
            cribado.get_nivel_riesgo_display(),
            cribado.get_resultado_display(),
            'Sí' if cribado.requiere_referencia else 'No',
            'Sí' if cribado.leucocoria else 'No',
            cribado.get_tipo_cancer_sospechado_display() if cribado.tipo_cancer_sospechado else 'Sin definir',
            sintomas_presentes or 'Ninguno',
        ])

    registrar_actividad(
        usuario=request.user,
        accion='Exportar Cribados CSV',
        modelo='CuestionarioCribado',
        objeto_id=str(request.user.id),
        objeto_repr=request.user.username,
        descripcion=f'Exportación de {cribados.count()} cribados FACCI a CSV',
    )

    return response
