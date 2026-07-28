from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.auth_app.models import CustomUser
from apps.core.decorators import requiere_acceso
from apps.pacientes.models import Paciente

from .models import EvaluacionPsicosocial


def _scope_pacientes(usuario):
    if usuario.rol in [CustomUser.Rol.MEDICO, CustomUser.Rol.PEDIATRA]:
        return Paciente.objects.filter(medico_asignado=usuario)
    if usuario.rol == CustomUser.Rol.ONCOLOGO:
        return Paciente.objects.filter(
            referencias__especialista_destino=usuario
        ).distinct()
    return Paciente.objects.all()


def _notificar_riesgo_alto(evaluacion):
    try:
        from apps.notificaciones.models import Notificacion
        from apps.notificaciones.services import crear_notificacion
        from django.urls import reverse
        url = reverse('psicosocial:detalle', kwargs={'pk': str(evaluacion.pk)})
        es_critico = evaluacion.nivel_riesgo == EvaluacionPsicosocial.NivelRiesgo.CRITICO

        destinatarios = list(CustomUser.objects.filter(
            rol__in=[CustomUser.Rol.ADMIN, CustomUser.Rol.PERSONAL_FACCI, CustomUser.Rol.TRABAJADORA_SOCIAL],
            is_active=True,
        ))
        if evaluacion.paciente.medico_asignado_id:
            destinatarios.append(evaluacion.paciente.medico_asignado)

        for usuario in destinatarios:
            crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.TipoNotificacion.ALERTA_CLINICA,
                modulo='Psicosocial',
                prioridad=Notificacion.Prioridad.CRITICA if es_critico else Notificacion.Prioridad.ALTA,
                titulo=f'{"CRÍTICO — " if es_critico else ""}Riesgo psicosocial {evaluacion.get_nivel_riesgo_display()}: {evaluacion.paciente.nombre_completo}',
                mensaje=(
                    f'Evaluación psicosocial con puntaje {evaluacion.puntaje_total}/24 '
                    f'({evaluacion.get_nivel_riesgo_display()}). Intervención {"urgente" if es_critico else "recomendada"}.'
                ),
                accion_url=url,
                accion_texto='Ver evaluación',
                objeto=evaluacion,
                icono_nombre='emergency' if es_critico else 'family_restroom',
                clave_dedupe=f'psico:{evaluacion.pk}:riesgo:{usuario.pk}',
            )
    except Exception:
        pass


def _choices_context():
    E = EvaluacionPsicosocial
    return {
        'ingresos': E.IngresoMensual.choices,
        'dificultades': E.Dificultad.choices,
        'condiciones_vivienda': E.CondicionVivienda.choices,
        'tipos_vivienda': E.TipoVivienda.choices,
        'parentescos': E.Parentesco.choices,
        'apoyos_familiar': E.ApoyoFamiliar.choices,
        'estados_emocionales': E.EstadoEmocional.choices,
        'impactos_emocionales': E.ImpactoEmocional.choices,
    }


@login_required
@requiere_acceso('puede_ver_psicosocial')
def lista_view(request):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    evaluaciones = EvaluacionPsicosocial.objects.select_related('paciente', 'evaluador')
    roles_vista_global = [CustomUser.Rol.ADMIN, CustomUser.Rol.PERSONAL_FACCI, CustomUser.Rol.TRABAJADORA_SOCIAL]
    if request.user.rol not in roles_vista_global:
        pacientes = _scope_pacientes(request.user)
        evaluaciones = evaluaciones.filter(paciente__in=pacientes)

    nivel = request.GET.get('nivel', '')
    q = request.GET.get('q', '').strip()
    paciente_pk = request.GET.get('paciente', '')

    if nivel and nivel in EvaluacionPsicosocial.NivelRiesgo.values:
        evaluaciones = evaluaciones.filter(nivel_riesgo=nivel)
    if q:
        evaluaciones = evaluaciones.filter(
            paciente__nombres__icontains=q
        ) | evaluaciones.filter(paciente__apellidos__icontains=q)
    if paciente_pk:
        evaluaciones = evaluaciones.filter(paciente__pk=paciente_pk)

    evaluaciones = evaluaciones.distinct().order_by('-fecha_evaluacion')
    total = evaluaciones.count()

    context = {
        'evaluaciones': evaluaciones,
        'total': total,
        'criticos': evaluaciones.filter(nivel_riesgo=EvaluacionPsicosocial.NivelRiesgo.CRITICO).count(),
        'altos': evaluaciones.filter(nivel_riesgo=EvaluacionPsicosocial.NivelRiesgo.ALTO).count(),
        'niveles': EvaluacionPsicosocial.NivelRiesgo.choices,
        'nivel_actual': nivel,
        'q': q,
    }
    return render(request, 'psicosocial/lista.html', context)


@login_required
@requiere_acceso('puede_gestionar_psicosocial')
def crear_view(request, paciente_pk=None):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    paciente_preseleccionado = None
    if paciente_pk:
        paciente_preseleccionado = get_object_or_404(Paciente, pk=paciente_pk)

    if request.method == 'POST':
        paciente_id = request.POST.get('paciente', '').strip()

        paciente = None
        errors = []
        if not paciente_id:
            errors.append('Seleccione un paciente.')
        else:
            try:
                paciente = Paciente.objects.get(pk=paciente_id)
            except Paciente.DoesNotExist:
                errors.append('Paciente no encontrado.')

        if errors:
            for err in errors:
                messages.error(request, err)
            return _render_crear(request, paciente_preseleccionado)

        import datetime
        hace_30_dias = timezone.now().date() - datetime.timedelta(days=30)
        eval_reciente = EvaluacionPsicosocial.objects.filter(
            paciente=paciente,
            fecha_evaluacion__gte=hace_30_dias
        ).first()

        confirmar_duplicado = request.POST.get('confirmar_duplicado') == '1'
        if eval_reciente and not confirmar_duplicado:
            messages.warning(
                request,
                f'El paciente {paciente.nombre_completo} ya cuenta con una evaluación psicosocial reciente del '
                f'{eval_reciente.fecha_evaluacion.strftime("%d/%m/%Y")}. Vuelva a presionar Guardar si confirma crear una nueva.'
            )
            return _render_crear(request, paciente, extra_context={'confirmar_duplicado': True})

        def post_bool(name, default=False):
            return request.POST.get(name, '') == 'si'

        def post_str(name, default=''):
            return request.POST.get(name, default).strip()

        evaluacion = EvaluacionPsicosocial(
            paciente=paciente,
            evaluador=request.user,
            # Cuidador
            cuidador_principal_nombre=post_str('cuidador_principal_nombre'),
            parentesco_cuidador=post_str('parentesco_cuidador'),
            personas_en_hogar=int(request.POST.get('personas_en_hogar', 1) or 1),
            tipo_vivienda=post_str('tipo_vivienda'),
            # Económica
            ingreso_mensual=post_str('ingreso_mensual', EvaluacionPsicosocial.IngresoMensual.MEDIO),
            tiene_seguro_medico=post_bool('tiene_seguro_medico'),
            dificultad_medicamentos=post_str('dificultad_medicamentos', EvaluacionPsicosocial.Dificultad.NINGUNA),
            dificultad_transporte=post_str('dificultad_transporte', EvaluacionPsicosocial.Dificultad.NINGUNA),
            # Vivienda
            condicion_vivienda=post_str('condicion_vivienda', EvaluacionPsicosocial.CondicionVivienda.ADECUADA),
            hacinamiento=post_bool('hacinamiento'),
            servicios_basicos_ausentes=post_bool('servicios_basicos_ausentes'),
            # Apoyo
            apoyo_familiar=post_str('apoyo_familiar', EvaluacionPsicosocial.ApoyoFamiliar.BUENO),
            cuidador_es_unico=post_bool('cuidador_es_unico'),
            # Cuidador
            estado_emocional_cuidador=post_str('estado_emocional_cuidador', EvaluacionPsicosocial.EstadoEmocional.ESTABLE),
            cuidador_perdio_trabajo=post_bool('cuidador_perdio_trabajo'),
            cuidador_requiere_apoyo_psicologico=post_bool('cuidador_requiere_apoyo_psicologico'),
            # Paciente
            nino_en_edad_escolar=post_bool('nino_en_edad_escolar'),
            abandono_escolar=post_bool('abandono_escolar'),
            impacto_emocional_paciente=post_str('impacto_emocional_paciente', EvaluacionPsicosocial.ImpactoEmocional.LEVE),
            # Plan
            necesidades_identificadas=post_str('necesidades_identificadas'),
            acciones_recomendadas=post_str('acciones_recomendadas'),
            observaciones=post_str('observaciones'),
            requiere_seguimiento_social=post_bool('requiere_seguimiento_social'),
            proxima_evaluacion=parse_date(request.POST.get('proxima_evaluacion', '') or ''),
        )
        evaluacion.save()

        if evaluacion.nivel_riesgo in [
            EvaluacionPsicosocial.NivelRiesgo.ALTO,
            EvaluacionPsicosocial.NivelRiesgo.CRITICO,
        ]:
            _notificar_riesgo_alto(evaluacion)

        messages.success(
            request,
            f'Evaluación {evaluacion.codigo} registrada. '
            f'Nivel de riesgo: {evaluacion.get_nivel_riesgo_display()} (puntaje {evaluacion.puntaje_total}/24).'
        )
        return redirect('psicosocial:detalle', pk=str(evaluacion.pk))

    return _render_crear(request, paciente_preseleccionado)


def _render_crear(request, paciente_preseleccionado, extra_context=None):
    pacientes = _scope_pacientes(request.user).order_by('apellidos', 'nombres')
    context = {
        'pacientes': pacientes,
        'paciente_preseleccionado': paciente_preseleccionado,
        'hoy': timezone.now().date().isoformat(),
        **_choices_context(),
    }
    if extra_context:
        context.update(extra_context)
    return render(request, 'psicosocial/crear.html', context)


@login_required
@requiere_acceso('puede_ver_psicosocial')
def detalle_view(request, pk):
    if request.user.rol == CustomUser.Rol.PADRE_TUTOR:
        return redirect('padres:estado')

    evaluacion = get_object_or_404(
        EvaluacionPsicosocial.objects.select_related('paciente', 'evaluador'),
        pk=pk,
    )
    evaluaciones_previas = (
        EvaluacionPsicosocial.objects
        .filter(paciente=evaluacion.paciente)
        .exclude(pk=pk)
        .order_by('-fecha_evaluacion')[:5]
    )
    context = {
        'evaluacion': evaluacion,
        'evaluaciones_previas': evaluaciones_previas,
        **_choices_context(),
    }
    return render(request, 'psicosocial/detalle.html', context)
