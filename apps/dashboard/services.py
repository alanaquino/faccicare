from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from apps.cribado.models import CuestionarioCribado
from apps.documentos.models import DocumentoMedico, SolicitudDocumento
from apps.pacientes.models import Paciente
from apps.referencias.models import ReferenciaMedica
from apps.seguimiento.models import SeguimientoPaciente

from .models import AlertaClinica


ESTADOS_ABIERTOS = [
    AlertaClinica.Estado.PENDIENTE,
    AlertaClinica.Estado.REVISADA,
]

ESTADOS_CERRADOS = [
    AlertaClinica.Estado.RESUELTA,
    AlertaClinica.Estado.DESCARTADA,
]


def _fecha_limite(base=None, dias=0, horas=0):
    base = base or timezone.now()
    if isinstance(base, datetime):
        dt = base
    else:
        dt = datetime.combine(base, time.min)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt + timedelta(days=dias, hours=horas)


def _sintomas_positivos(cribado):
    sintomas = []
    for campo in CuestionarioCribado.CAMPOS_SINTOMAS:
        if getattr(cribado, campo):
            sintomas.append(str(cribado._meta.get_field(campo).verbose_name))
    return ', '.join(sintomas) if sintomas else 'Sin sintomas positivos registrados.'


def _tiene_referencia_posterior(cribado):
    qs = ReferenciaMedica.objects.filter(paciente=cribado.paciente)
    if cribado.fecha_evaluacion:
        qs = qs.filter(fecha_referencia__gte=cribado.fecha_evaluacion)
    return qs.exists()


def _tiene_seguimiento_posterior(paciente, fecha):
    qs = SeguimientoPaciente.objects.filter(paciente=paciente)
    if fecha:
        qs = qs.filter(fecha_seguimiento__gt=fecha)
    return qs.exists()


def _crear_o_actualizar_alerta(clave_dedupe, **datos):
    datos.setdefault('estado', AlertaClinica.Estado.PENDIENTE)
    with transaction.atomic():
        alerta, creada = AlertaClinica.objects.select_for_update().get_or_create(
            clave_dedupe=clave_dedupe,
            defaults=datos,
        )
        if creada or alerta.estado in ESTADOS_CERRADOS:
            return alerta

        campos_actualizables = [
            'paciente',
            'cribado',
            'referencia',
            'seguimiento',
            'documento',
            'solicitud_documento',
            'tipo_alerta',
            'prioridad',
            'titulo',
            'descripcion',
            'fecha_limite',
        ]
        cambios = []
        for campo in campos_actualizables:
            if campo in datos and getattr(alerta, campo) != datos[campo]:
                setattr(alerta, campo, datos[campo])
                cambios.append(campo)
        if cambios:
            alerta.save(update_fields=cambios + ['updated_at'])
        return alerta


def _resolver_alerta_automatica(clave_dedupe, comentario):
    AlertaClinica.objects.filter(
        clave_dedupe=clave_dedupe,
        estado__in=ESTADOS_ABIERTOS,
    ).update(
        estado=AlertaClinica.Estado.RESUELTA,
        fecha_revision=timezone.now(),
        comentario_cierre=comentario,
    )


def _prioridad_por_antiguedad(fecha_base, dias_limite, prioridad_base, prioridad_vencida):
    if fecha_base and _fecha_limite(fecha_base, dias=dias_limite) < timezone.now():
        return prioridad_vencida
    return prioridad_base


def generar_alertas_cribado(cribado):
    sintomas_clave = f'cribado:{cribado.id}:sintomas_alarma'
    referencia_clave = f'cribado:{cribado.id}:sospechoso_sin_referencia'
    hallazgos = _sintomas_positivos(cribado)

    if cribado.nivel_riesgo == CuestionarioCribado.NivelRiesgo.ALTO or cribado.tiene_alarma_mayor:
        _crear_o_actualizar_alerta(
            sintomas_clave,
            paciente=cribado.paciente,
            cribado=cribado,
            tipo_alerta=AlertaClinica.TipoAlerta.SINTOMAS_ALARMA,
            prioridad=AlertaClinica.Prioridad.CRITICA,
            titulo='Sintomas de alarma detectados en cribado',
            descripcion=(
                f'Cribado FACCI con {cribado.get_nivel_riesgo_display()} y '
                f'{cribado.puntaje_total}/{len(CuestionarioCribado.CAMPOS_SINTOMAS)} sintomas. '
                f'Hallazgos: {hallazgos}'
            ),
            fecha_limite=timezone.now(),
        )
    else:
        _resolver_alerta_automatica(sintomas_clave, 'El cribado ya no mantiene sintomas de alarma.')

    if cribado.requiere_referencia and not _tiene_referencia_posterior(cribado):
        _crear_o_actualizar_alerta(
            referencia_clave,
            paciente=cribado.paciente,
            cribado=cribado,
            tipo_alerta=AlertaClinica.TipoAlerta.SOSPECHOSO_SIN_REFERENCIA,
            prioridad=AlertaClinica.Prioridad.ALTA,
            titulo='Caso sospechoso sin referencia creada',
            descripcion=(
                'El cribado requiere referencia a especialista y todavia no existe '
                f'una referencia posterior asociada. Hallazgos: {hallazgos}'
            ),
            fecha_limite=_fecha_limite(cribado.fecha_evaluacion, dias=1),
        )
    else:
        _resolver_alerta_automatica(referencia_clave, 'Existe referencia posterior o el cribado ya no la requiere.')


def generar_alertas_referencia(referencia):
    alta_clave = f'referencia:{referencia.id}:alta_prioridad_sin_revision'
    seguimiento_clave = f'referencia:{referencia.id}:sin_seguimiento'
    cerrada = referencia.estado in [
        ReferenciaMedica.EstadoReferencia.COMPLETADA,
        ReferenciaMedica.EstadoReferencia.CANCELADA,
    ]

    if cerrada:
        _resolver_alerta_automatica(alta_clave, 'Referencia cerrada.')
        _resolver_alerta_automatica(seguimiento_clave, 'Referencia cerrada.')
        if referencia.cuestionario_id:
            generar_alertas_cribado(referencia.cuestionario)
        return

    if (
        referencia.estado == ReferenciaMedica.EstadoReferencia.PENDIENTE
        and referencia.prioridad in [ReferenciaMedica.Prioridad.ALTA, ReferenciaMedica.Prioridad.URGENTE]
    ):
        prioridad = (
            AlertaClinica.Prioridad.CRITICA
            if referencia.prioridad == ReferenciaMedica.Prioridad.URGENTE
            else AlertaClinica.Prioridad.ALTA
        )
        _crear_o_actualizar_alerta(
            alta_clave,
            paciente=referencia.paciente,
            referencia=referencia,
            cribado=referencia.cuestionario,
            tipo_alerta=AlertaClinica.TipoAlerta.ALTA_PRIORIDAD_SIN_REVISION,
            prioridad=prioridad,
            titulo='Referencia de alta prioridad pendiente de revision',
            descripcion=(
                f'Referencia {referencia.codigo} pendiente hacia {referencia.hospital_destino or "destino sin asignar"}. '
                f'Motivo: {referencia.motivo_referencia}'
            ),
            fecha_limite=_fecha_limite(referencia.fecha_referencia, dias=1),
        )
    else:
        _resolver_alerta_automatica(alta_clave, 'La referencia ya no esta pendiente de revision prioritaria.')

    if not _tiene_seguimiento_posterior(referencia.paciente, referencia.fecha_referencia):
        fecha_limite = _fecha_limite(referencia.fecha_referencia, dias=3)
        prioridad = AlertaClinica.Prioridad.MEDIA
        if referencia.prioridad in [ReferenciaMedica.Prioridad.ALTA, ReferenciaMedica.Prioridad.URGENTE]:
            prioridad = AlertaClinica.Prioridad.ALTA
        if fecha_limite < timezone.now():
            prioridad = AlertaClinica.Prioridad.CRITICA if referencia.es_urgente else AlertaClinica.Prioridad.ALTA

        _crear_o_actualizar_alerta(
            seguimiento_clave,
            paciente=referencia.paciente,
            referencia=referencia,
            cribado=referencia.cuestionario,
            tipo_alerta=AlertaClinica.TipoAlerta.REFERENCIA_SIN_SEGUIMIENTO,
            prioridad=prioridad,
            titulo='Referencia sin seguimiento posterior',
            descripcion=(
                f'La referencia {referencia.codigo} fue creada y aun no registra un seguimiento clinico posterior.'
            ),
            fecha_limite=fecha_limite,
        )
    else:
        _resolver_alerta_automatica(seguimiento_clave, 'Ya existe seguimiento posterior a la referencia.')

    if referencia.cuestionario_id:
        generar_alertas_cribado(referencia.cuestionario)


def generar_alertas_seguimiento(seguimiento):
    critico_clave = f'seguimiento:{seguimiento.id}:caso_critico'
    vencido_clave = f'seguimiento:{seguimiento.id}:proxima_fecha_seguimiento_vencida'

    if seguimiento.requiere_hospitalizacion:
        _crear_o_actualizar_alerta(
            critico_clave,
            paciente=seguimiento.paciente,
            seguimiento=seguimiento,
            tipo_alerta=AlertaClinica.TipoAlerta.CASO_CRITICO,
            prioridad=AlertaClinica.Prioridad.CRITICA,
            titulo='Seguimiento critico requiere atencion inmediata',
            descripcion=(
                f'El seguimiento registra necesidad de hospitalizacion. Estado clinico: {seguimiento.estado_clinico}'
            ),
            fecha_limite=timezone.now(),
        )
    else:
        _resolver_alerta_automatica(critico_clave, 'El seguimiento ya no requiere hospitalizacion.')

    if seguimiento.proxima_fecha_seguimiento and seguimiento.proxima_fecha_seguimiento < timezone.now():
        tiene_revision = SeguimientoPaciente.objects.filter(
            paciente=seguimiento.paciente,
            fecha_seguimiento__gt=seguimiento.proxima_fecha_seguimiento,
        ).exclude(pk=seguimiento.pk).exists()
        if not tiene_revision:
            _crear_o_actualizar_alerta(
                vencido_clave,
                paciente=seguimiento.paciente,
                seguimiento=seguimiento,
                tipo_alerta=AlertaClinica.TipoAlerta.SEGUIMIENTO_PENDIENTE,
                prioridad=AlertaClinica.Prioridad.ALTA,
                titulo='Seguimiento vencido o pendiente',
                descripcion=(
                    f'El próximo seguimiento venció el {seguimiento.proxima_fecha_seguimiento:%d/%m/%Y %H:%M} '
                    'y no existe una revision posterior registrada.'
                ),
                fecha_limite=seguimiento.proxima_fecha_seguimiento,
            )
        else:
            _resolver_alerta_automatica(vencido_clave, 'Ya existe revision posterior al seguimiento vencido.')
    else:
        _resolver_alerta_automatica(vencido_clave, 'El próximo seguimiento no esta vencido.')

    for referencia in ReferenciaMedica.objects.filter(paciente=seguimiento.paciente):
        generar_alertas_referencia(referencia)
    generar_alertas_paciente(seguimiento.paciente)


def generar_alertas_documento(documento):
    clave = f'documento:{documento.id}:pendiente_revision'
    if documento.estado in [DocumentoMedico.EstadoDocumento.PENDIENTE, DocumentoMedico.EstadoDocumento.CORRECCION]:
        fecha_limite = _fecha_limite(documento.created_at, dias=3)
        prioridad = AlertaClinica.Prioridad.ALTA if fecha_limite < timezone.now() else AlertaClinica.Prioridad.MEDIA
        _crear_o_actualizar_alerta(
            clave,
            paciente=documento.paciente,
            documento=documento,
            tipo_alerta=AlertaClinica.TipoAlerta.DOCUMENTO_PENDIENTE,
            prioridad=prioridad,
            titulo='Documento clinico pendiente de revision',
            descripcion=f'Documento {documento.get_tipo_documento_display()} pendiente para {documento.paciente.nombre_completo}.',
            fecha_limite=fecha_limite,
        )
    else:
        _resolver_alerta_automatica(clave, 'Documento revisado.')


def generar_alertas_solicitud_documento(solicitud):
    clave = f'solicitud-documento:{solicitud.id}:pendiente'
    if solicitud.estado in [SolicitudDocumento.EstadoSolicitud.PENDIENTE, SolicitudDocumento.EstadoSolicitud.CORRECCION]:
        fecha_limite = _fecha_limite(solicitud.created_at, dias=7)
        prioridad = AlertaClinica.Prioridad.ALTA if fecha_limite < timezone.now() else AlertaClinica.Prioridad.MEDIA
        _crear_o_actualizar_alerta(
            clave,
            paciente=solicitud.paciente,
            solicitud_documento=solicitud,
            tipo_alerta=AlertaClinica.TipoAlerta.DOCUMENTO_PENDIENTE,
            prioridad=prioridad,
            titulo='Solicitud de documento pendiente',
            descripcion=f'Solicitud pendiente: {solicitud.titulo}.',
            fecha_limite=fecha_limite,
        )
    else:
        _resolver_alerta_automatica(clave, 'Solicitud de documento cerrada.')


def generar_alertas_paciente(paciente):
    clave = f'paciente:{paciente.id}:alta_prioridad_sin_revision'
    requiere_revision = paciente.estado_actual in [
        Paciente.EstadoPaciente.REFERIDO,
        Paciente.EstadoPaciente.EN_TRATAMIENTO,
    ]
    if requiere_revision and not paciente.seguimientos.exists():
        _crear_o_actualizar_alerta(
            clave,
            paciente=paciente,
            tipo_alerta=AlertaClinica.TipoAlerta.ALTA_PRIORIDAD_SIN_REVISION,
            prioridad=AlertaClinica.Prioridad.ALTA,
            titulo='Paciente de alta prioridad sin revision medica',
            descripcion=(
                f'El paciente esta en estado {paciente.get_estado_actual_display()} '
                'y aun no registra seguimiento clinico.'
            ),
            fecha_limite=_fecha_limite(paciente.updated_at or paciente.created_at, dias=2),
        )
    else:
        _resolver_alerta_automatica(clave, 'El paciente ya tiene seguimiento o no esta en alta prioridad.')


def generar_alertas_pendientes():
    for cribado in CuestionarioCribado.objects.select_related('paciente').filter(
        nivel_riesgo=CuestionarioCribado.NivelRiesgo.ALTO
    ):
        generar_alertas_cribado(cribado)

    referencias = ReferenciaMedica.objects.select_related('paciente', 'cuestionario').exclude(
        estado__in=[
            ReferenciaMedica.EstadoReferencia.COMPLETADA,
            ReferenciaMedica.EstadoReferencia.CANCELADA,
        ]
    )
    for referencia in referencias:
        generar_alertas_referencia(referencia)

    seguimientos = SeguimientoPaciente.objects.select_related('paciente').filter(
        requiere_hospitalizacion=True
    )
    for seguimiento in seguimientos:
        generar_alertas_seguimiento(seguimiento)

    seguimientos_vencidos = SeguimientoPaciente.objects.select_related('paciente').filter(
        proxima_fecha_seguimiento__lt=timezone.now()
    )
    for seguimiento in seguimientos_vencidos:
        generar_alertas_seguimiento(seguimiento)

    for documento in DocumentoMedico.objects.select_related('paciente').filter(
        estado__in=[DocumentoMedico.EstadoDocumento.PENDIENTE, DocumentoMedico.EstadoDocumento.CORRECCION]
    ):
        generar_alertas_documento(documento)

    for solicitud in SolicitudDocumento.objects.select_related('paciente').filter(
        estado__in=[SolicitudDocumento.EstadoSolicitud.PENDIENTE, SolicitudDocumento.EstadoSolicitud.CORRECCION]
    ):
        generar_alertas_solicitud_documento(solicitud)

    for paciente in Paciente.objects.filter(
        estado_actual__in=[Paciente.EstadoPaciente.REFERIDO, Paciente.EstadoPaciente.EN_TRATAMIENTO]
    ):
        generar_alertas_paciente(paciente)


def resumen_alertas(queryset=None):
    queryset = queryset if queryset is not None else AlertaClinica.objects.all()
    abiertas = queryset.filter(estado__in=ESTADOS_ABIERTOS)
    return {
        'pendientes': queryset.filter(estado=AlertaClinica.Estado.PENDIENTE).count(),
        'abiertas': abiertas.count(),
        'criticas': abiertas.filter(prioridad=AlertaClinica.Prioridad.CRITICA).count(),
        'alta': abiertas.filter(prioridad=AlertaClinica.Prioridad.ALTA).count(),
        'vencidas': abiertas.filter(fecha_limite__lt=timezone.now()).count(),
        'ultimas': list(queryset.select_related('paciente').order_by('-fecha_creacion')[:5]),
    }
