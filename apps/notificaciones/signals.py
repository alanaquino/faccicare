from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.cribado.models import CuestionarioCribado
from apps.dashboard.models import AlertaClinica
from apps.documentos.models import DocumentoMedico, SolicitudDocumento
from apps.pacientes.models import Paciente
from apps.padres.models import ReporteSintoma
from apps.referencias.models import ReferenciaMedica
from apps.reportes.models import ReporteGenerado
from apps.seguimiento.models import SeguimientoPaciente

from .models import Notificacion
from .services import crear_notificacion, reverse_or_path, usuarios_del_paciente


def _previous(instance, fields):
    if not instance.pk:
        return {}
    sender = instance.__class__
    old = sender.objects.filter(pk=instance.pk).first()
    if not old:
        return {}
    return {field: getattr(old, field, None) for field in fields}


def _changed(instance, field):
    previous = getattr(instance, '_notif_previous', {})
    return previous and previous.get(field) != getattr(instance, field, None)


def _priority_from_referencia(referencia):
    if referencia.prioridad == ReferenciaMedica.Prioridad.URGENTE:
        return Notificacion.Prioridad.CRITICA
    if referencia.prioridad == ReferenciaMedica.Prioridad.ALTA:
        return Notificacion.Prioridad.ALTA
    if referencia.prioridad == ReferenciaMedica.Prioridad.BAJA:
        return Notificacion.Prioridad.BAJA
    return Notificacion.Prioridad.MEDIA


def _priority_from_alerta(alerta):
    if alerta.prioridad == AlertaClinica.Prioridad.CRITICA:
        return Notificacion.Prioridad.CRITICA
    if alerta.prioridad == AlertaClinica.Prioridad.ALTA:
        return Notificacion.Prioridad.ALTA
    if alerta.prioridad == AlertaClinica.Prioridad.BAJA:
        return Notificacion.Prioridad.BAJA
    return Notificacion.Prioridad.MEDIA


@receiver(pre_save, sender=ReferenciaMedica, dispatch_uid='notificaciones_prev_referencia')
@receiver(pre_save, sender=Paciente, dispatch_uid='notificaciones_prev_paciente')
@receiver(pre_save, sender=SolicitudDocumento, dispatch_uid='notificaciones_prev_solicitud')
@receiver(pre_save, sender=AlertaClinica, dispatch_uid='notificaciones_prev_alerta')
def guardar_estado_previo(sender, instance, **kwargs):
    campos = {
        ReferenciaMedica: ['estado', 'especialista_destino_id', 'prioridad', 'fecha_cita'],
        Paciente: ['estado_actual', 'diagnostico', 'medico_asignado_id'],
        SolicitudDocumento: ['estado', 'documento_asociado_id'],
        AlertaClinica: ['estado', 'prioridad'],
    }.get(sender, [])
    instance._notif_previous = _previous(instance, campos)


def _destinatarios_urgente(instance):
    """Devuelve oncólogos y admins activos para broadcast de referencia urgente/alta."""
    from apps.auth_app.models import CustomUser
    qs = CustomUser.objects.filter(
        rol__in=[CustomUser.Rol.ADMIN, CustomUser.Rol.ONCOLOGO],
        is_active=True,
    )
    if instance.especialista_destino_id:
        qs = qs.exclude(pk=instance.especialista_destino_id)
    return list(qs)


@receiver(post_save, sender=ReferenciaMedica, dispatch_uid='notificaciones_save_referencia')
def notificar_referencia(sender, instance, created, **kwargs):
    prioridad = _priority_from_referencia(instance)
    url = reverse_or_path('referencias:detalle', pk=instance.pk)
    es_urgente = instance.prioridad == ReferenciaMedica.Prioridad.URGENTE
    es_alta_o_urgente = instance.prioridad in [
        ReferenciaMedica.Prioridad.URGENTE,
        ReferenciaMedica.Prioridad.ALTA,
    ]

    if created:
        # Notificar al especialista destino (si hay)
        if instance.especialista_destino_id:
            crear_notificacion(
                usuario=instance.especialista_destino,
                tipo=Notificacion.TipoNotificacion.REFERENCIA,
                modulo='Referencias',
                prioridad=prioridad,
                titulo=f'{"URGENTE — " if es_urgente else ""}Referencia recibida - {instance.paciente.nombre_completo}',
                mensaje=f'Referencia {instance.codigo} pendiente hacia {instance.hospital_destino or "destino sin asignar"}.',
                accion_url=url,
                accion_texto='Ver referencia',
                objeto=instance,
                icono_nombre='emergency' if es_urgente else 'send',
                clave_dedupe=f'referencia:{instance.pk}:recibida:{instance.especialista_destino_id}',
            )

        # Broadcast a oncólogos y admins para referencias URGENTE o ALTA
        if es_alta_o_urgente:
            titulo_broadcast = (
                f'URGENTE — Referencia sin asignar: {instance.paciente.nombre_completo}'
                if not instance.especialista_destino_id
                else f'Referencia {instance.get_prioridad_display()} — {instance.paciente.nombre_completo}'
            )
            mensaje_broadcast = (
                f'Referencia {instance.codigo} con prioridad {instance.get_prioridad_display()} '
                f'hacia {instance.hospital_destino or "destino sin asignar"}. Motivo: {instance.motivo_referencia[:120]}'
            )
            for usuario in _destinatarios_urgente(instance):
                crear_notificacion(
                    usuario=usuario,
                    tipo=Notificacion.TipoNotificacion.REFERENCIA,
                    modulo='Referencias',
                    prioridad=prioridad,
                    titulo=titulo_broadcast,
                    mensaje=mensaje_broadcast,
                    accion_url=url,
                    accion_texto='Ver referencia',
                    objeto=instance,
                    icono_nombre='emergency' if es_urgente else 'priority_high',
                    clave_dedupe=f'referencia:{instance.pk}:broadcast:{usuario.pk}',
                )

    if not created and _changed(instance, 'especialista_destino_id') and instance.especialista_destino_id:
        crear_notificacion(
            usuario=instance.especialista_destino,
            tipo=Notificacion.TipoNotificacion.REFERENCIA,
            modulo='Referencias',
            prioridad=prioridad,
            titulo=f'Referencia asignada - {instance.paciente.nombre_completo}',
            mensaje=f'Se le asigno la referencia {instance.codigo}.',
            accion_url=url,
            accion_texto='Ver referencia',
            objeto=instance,
            clave_dedupe=f'referencia:{instance.pk}:asignada:{instance.especialista_destino_id}',
        )

    if not created and _changed(instance, 'estado'):
        for usuario in {instance.medico_referente, instance.especialista_destino}:
            if usuario:
                crear_notificacion(
                    usuario=usuario,
                    tipo=Notificacion.TipoNotificacion.REFERENCIA,
                    modulo='Referencias',
                    prioridad=prioridad,
                    titulo=f'Referencia actualizada - {instance.paciente.nombre_completo}',
                    mensaje=f'La referencia {instance.codigo} cambio a {instance.get_estado_display()}.',
                    accion_url=url,
                    accion_texto='Ver referencia',
                    objeto=instance,
                    clave_dedupe=f'referencia:{instance.pk}:estado:{instance.estado}:{usuario.pk}',
                )


@receiver(post_save, sender=SeguimientoPaciente, dispatch_uid='notificaciones_save_seguimiento')
def notificar_seguimiento(sender, instance, created, **kwargs):
    if not created:
        return
    for usuario in usuarios_del_paciente(instance.paciente, incluir_medico=False, incluir_creador=False):
        crear_notificacion(
            usuario=usuario,
            tipo=Notificacion.TipoNotificacion.SEGUIMIENTO,
            modulo='Seguimiento',
            prioridad=Notificacion.Prioridad.ALTA if instance.requiere_hospitalizacion else Notificacion.Prioridad.MEDIA,
            titulo=f'Nuevo seguimiento - {instance.paciente.nombre_completo}',
            mensaje=f'Se registro un seguimiento clinico: {instance.estado_clinico}.',
            accion_url='padres:evolucion' if getattr(usuario, 'rol', '') == 'PADRE_TUTOR' else reverse_or_path('seguimiento:lista'),
            accion_texto='Ver seguimiento',
            objeto=instance,
            clave_dedupe=f'seguimiento:{instance.pk}:creado:{usuario.pk}',
        )


@receiver(post_save, sender=AlertaClinica, dispatch_uid='notificaciones_save_alerta')
def notificar_alerta_clinica(sender, instance, created, **kwargs):
    abierta = instance.estado in [AlertaClinica.Estado.PENDIENTE, AlertaClinica.Estado.REVISADA]
    prioritaria = instance.prioridad in [AlertaClinica.Prioridad.ALTA, AlertaClinica.Prioridad.CRITICA]
    if not abierta or not prioritaria:
        return

    for usuario in usuarios_del_paciente(instance.paciente, incluir_tutor=False):
        crear_notificacion(
            usuario=usuario,
            tipo=Notificacion.TipoNotificacion.ALERTA_CLINICA,
            modulo='Alertas',
            prioridad=_priority_from_alerta(instance),
            titulo=instance.titulo,
            mensaje=instance.descripcion,
            accion_url=instance.url_detalle,
            accion_texto='Ver alerta',
            objeto=instance,
            icono_nombre=instance.icono,
            clave_dedupe=f'alerta:{instance.pk}:prioritaria:{usuario.pk}',
        )


@receiver(post_save, sender=ReporteGenerado, dispatch_uid='notificaciones_save_reporte')
def notificar_reporte(sender, instance, created, **kwargs):
    if not created:
        return
    crear_notificacion(
        usuario=instance.generado_por,
        tipo=Notificacion.TipoNotificacion.REPORTE,
        modulo='Reportes',
        prioridad=Notificacion.Prioridad.BAJA,
        titulo='Reporte generado',
        mensaje=f'Reporte "{instance.get_tipo_reporte_display()}" registrado correctamente.',
        accion_url='reportes:generacion',
        accion_texto='Ver reporte',
        objeto=instance,
        clave_dedupe=f'reporte:{instance.pk}:generado:{instance.generado_por_id}',
    )


@receiver(post_save, sender=Paciente, dispatch_uid='notificaciones_save_paciente')
def notificar_paciente(sender, instance, created, **kwargs):
    url = reverse_or_path('pacientes:expediente', pk=instance.pk)
    if created and instance.medico_asignado_id:
        crear_notificacion(
            usuario=instance.medico_asignado,
            tipo=Notificacion.TipoNotificacion.PACIENTE,
            modulo='Pacientes',
            prioridad=Notificacion.Prioridad.MEDIA,
            titulo=f'Paciente asignado - {instance.nombre_completo}',
            mensaje=f'El expediente {instance.codigo_paciente} esta asignado a usted.',
            accion_url=url,
            accion_texto='Ver expediente',
            objeto=instance,
            clave_dedupe=f'paciente:{instance.pk}:asignado:{instance.medico_asignado_id}',
        )
    if not created and any(_changed(instance, campo) for campo in ['estado_actual', 'diagnostico', 'medico_asignado_id']):
        for usuario in usuarios_del_paciente(instance):
            accion = 'padres:estado' if getattr(usuario, 'rol', '') == 'PADRE_TUTOR' else url
            crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.TipoNotificacion.PACIENTE,
                modulo='Pacientes',
                prioridad=Notificacion.Prioridad.MEDIA,
                titulo=f'Expediente actualizado - {instance.nombre_completo}',
                mensaje=f'El expediente cambio a estado {instance.get_estado_actual_display()}.',
                accion_url=accion,
                accion_texto='Ver expediente',
                objeto=instance,
                clave_dedupe=f'paciente:{instance.pk}:actualizado:{instance.updated_at:%Y%m%d%H%M%S}:{usuario.pk}',
            )


@receiver(post_save, sender=CuestionarioCribado, dispatch_uid='notificaciones_save_cribado')
def notificar_cribado(sender, instance, created, **kwargs):
    if not created or instance.nivel_riesgo == CuestionarioCribado.NivelRiesgo.BAJO:
        return
    prioridad = (
        Notificacion.Prioridad.CRITICA
        if instance.nivel_riesgo == CuestionarioCribado.NivelRiesgo.ALTO
        else Notificacion.Prioridad.MEDIA
    )
    for usuario in usuarios_del_paciente(instance.paciente, incluir_tutor=False):
        crear_notificacion(
            usuario=usuario,
            tipo=Notificacion.TipoNotificacion.CRIBADO,
            modulo='Cribado',
            prioridad=prioridad,
            titulo=f'Cribado con riesgo - {instance.paciente.nombre_completo}',
            mensaje=f'Resultado {instance.get_resultado_display()} con puntaje {instance.puntaje_total}.',
            accion_url=reverse_or_path('cribado:detalle', pk=instance.pk),
            accion_texto='Ver cribado',
            objeto=instance,
            clave_dedupe=f'cribado:{instance.pk}:riesgo:{usuario.pk}',
        )


@receiver(post_save, sender=SolicitudDocumento, dispatch_uid='notificaciones_save_solicitud_documento')
def notificar_solicitud_documento(sender, instance, created, **kwargs):
    tutor_usuario = getattr(getattr(instance.paciente, 'padre_tutor', None), 'usuario', None)
    if tutor_usuario and instance.estado in [
        SolicitudDocumento.EstadoSolicitud.PENDIENTE,
        SolicitudDocumento.EstadoSolicitud.CORRECCION,
    ]:
        crear_notificacion(
            usuario=tutor_usuario,
            tipo=Notificacion.TipoNotificacion.ALERTA,
            modulo='Documentos',
            prioridad=Notificacion.Prioridad.ALTA if instance.estado == SolicitudDocumento.EstadoSolicitud.CORRECCION else Notificacion.Prioridad.MEDIA,
            titulo=f'Estudio Solicitado: {instance.titulo}',
            mensaje=f'El medico solicito "{instance.titulo}" para {instance.paciente.nombres}.',
            accion_url=f'/padres/documentos/subir/{instance.pk}/',
            accion_texto='Subir resultado',
            objeto=instance,
            clave_dedupe=f'solicitud:{instance.pk}:padre:{tutor_usuario.pk}',
        )

    if instance.estado == SolicitudDocumento.EstadoSolicitud.SUBIDO:
        for usuario in usuarios_del_paciente(instance.paciente, incluir_tutor=False):
            crear_notificacion(
                usuario=usuario,
                tipo=Notificacion.TipoNotificacion.DOCUMENTO,
                modulo='Documentos',
                prioridad=Notificacion.Prioridad.MEDIA,
                titulo=f'Resultado cargado - {instance.paciente.nombre_completo}',
                mensaje=f'El estudio "{instance.titulo}" fue cargado y requiere revision.',
                accion_url=reverse_or_path('pacientes:expediente', pk=instance.paciente_id),
                accion_texto='Revisar estudio',
                objeto=instance,
                clave_dedupe=f'solicitud:{instance.pk}:resultado:{usuario.pk}',
            )


@receiver(post_save, sender=DocumentoMedico, dispatch_uid='notificaciones_save_documento')
def notificar_documento(sender, instance, created, **kwargs):
    if not created:
        return
    if getattr(instance, '_notificaciones_skip_documento', False):
        return
    for usuario in usuarios_del_paciente(instance.paciente, incluir_tutor=False):
        if usuario == instance.subido_por:
            continue
        crear_notificacion(
            usuario=usuario,
            tipo=Notificacion.TipoNotificacion.DOCUMENTO,
            modulo='Documentos',
            prioridad=Notificacion.Prioridad.MEDIA,
            titulo='Nuevo documento recibido',
            mensaje=(
                f'El padre/tutor de {instance.paciente.nombre_completo} ha subido el documento '
                f'"{instance.nombre}" ({instance.get_tipo_documento_display()}) para revision.'
            ),
            accion_url=reverse_or_path('documentos:detalle', pk=instance.pk),
            accion_texto='Ver documento',
            objeto=instance,
            clave_dedupe=f'documento:{instance.pk}:cargado:{usuario.pk}',
        )


@receiver(post_save, sender=ReporteSintoma, dispatch_uid='notificaciones_save_reporte_sintoma')
def notificar_reporte_sintoma(sender, instance, created, **kwargs):
    if not created:
        return
    for usuario in usuarios_del_paciente(instance.paciente, incluir_tutor=False):
        crear_notificacion(
            usuario=usuario,
            tipo=Notificacion.TipoNotificacion.SINTOMAS,
            modulo='Pacientes',
            prioridad=Notificacion.Prioridad.ALTA if instance.gravedad == ReporteSintoma.Gravedad.SEVERA else Notificacion.Prioridad.MEDIA,
            titulo=f'Reporte de sintomas - {instance.paciente.nombre_completo}',
            mensaje=f'Gravedad: {instance.gravedad}. Sintomas: {instance.sintomas_str}. {instance.descripcion}',
            accion_url=reverse_or_path('pacientes:expediente', pk=instance.paciente_id),
            accion_texto='Ver expediente',
            objeto=instance,
            clave_dedupe=f'reporte-sintoma:{instance.pk}:personal:{usuario.pk}',
        )


