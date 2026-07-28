from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.cribado.models import CuestionarioCribado
from apps.dashboard.models import AlertaClinica
from apps.documentos.models import DocumentoMedico, SolicitudDocumento
from apps.pacientes.models import Paciente
from apps.referencias.models import ReferenciaMedica
from apps.reportes.models import ReporteGenerado
from apps.seguimiento.models import SeguimientoPaciente

from .audit import registrar_actividad
from .models import LogActividad


AUDIT_FIELDS = {
    Paciente: [
        'nombres', 'apellidos', 'fecha_nacimiento', 'sexo', 'provincia',
        'municipio', 'tipo_sangre', 'estado_actual', 'diagnostico',
        'medico_asignado_id',
    ],
    CuestionarioCribado: [
        *CuestionarioCribado.CAMPOS_SINTOMAS,
        'observaciones',
    ],
    ReferenciaMedica: [
        'estado', 'prioridad', 'hospital_destino_id', 'especialista_destino_id',
        'fecha_cita', 'observaciones',
    ],
    SeguimientoPaciente: [
        'fase_protocolo', 'estado_clinico', 'sintomas_actuales',
        'tratamiento_actual', 'medicamentos', 'observaciones',
        'proxima_fecha_seguimiento', 'requiere_hospitalizacion',
    ],
    DocumentoMedico: [
        'tipo_documento', 'descripcion', 'fecha_documento', 'estado',
    ],
    SolicitudDocumento: [
        'titulo', 'descripcion', 'estado', 'documento_asociado_id',
    ],
    AlertaClinica: [
        'estado', 'prioridad', 'fecha_revision', 'revisado_por_id',
        'comentario_cierre',
    ],
}


MODULOS = {
    Paciente: 'Pacientes',
    CuestionarioCribado: 'Cribado',
    ReferenciaMedica: 'Referencias',
    SeguimientoPaciente: 'Seguimiento',
    DocumentoMedico: 'Documentos',
    SolicitudDocumento: 'Documentos',
    AlertaClinica: 'Alertas',
    ReporteGenerado: 'Reportes',
}


def _get_previous(sender, instance):
    if not instance.pk:
        return {}
    previous = sender.objects.filter(pk=instance.pk).first()
    if not previous:
        return {}
    return {
        field: getattr(previous, field, None)
        for field in AUDIT_FIELDS.get(sender, [])
    }


def _changed_fields(sender, instance):
    previous = getattr(instance, '_audit_previous', {})
    if not previous:
        return []
    changed = []
    for field, old_value in previous.items():
        new_value = getattr(instance, field, None)
        if old_value != new_value:
            changed.append(field)
    return changed


def _usuario_modelo(instance):
    UserModel = get_user_model()
    for attr in (
        'creado_por',
        'medico',
        'medico_referente',
        'subido_por',
        'medico_solicitante',
        'generado_por',
        'revisado_por',
    ):
        user = getattr(instance, attr, None)
        if isinstance(user, UserModel):
            return user
    paciente = getattr(instance, 'paciente', None)
    user = getattr(paciente, 'creado_por', None)
    return user if isinstance(user, UserModel) else None


def _paciente_nombre(instance):
    paciente = getattr(instance, 'paciente', instance if isinstance(instance, Paciente) else None)
    return getattr(paciente, 'nombre_completo', str(instance))


def _descripcion_creacion(instance):
    if isinstance(instance, Paciente):
        return f'Paciente creado: {instance.nombre_completo} ({instance.codigo_paciente}).'
    if isinstance(instance, CuestionarioCribado):
        return f'Cribado creado para {_paciente_nombre(instance)} con nivel {instance.get_nivel_riesgo_display()}.'
    if isinstance(instance, ReferenciaMedica):
        return f'Referencia creada para {_paciente_nombre(instance)} hacia {instance.hospital_destino or "destino sin asignar"}.'
    if isinstance(instance, SeguimientoPaciente):
        return f'Seguimiento creado para {_paciente_nombre(instance)}.'
    if isinstance(instance, DocumentoMedico):
        return f'Documento {instance.get_tipo_documento_display()} creado para {_paciente_nombre(instance)}.'
    if isinstance(instance, SolicitudDocumento):
        return f'Solicitud de documento "{instance.titulo}" creada para {_paciente_nombre(instance)}.'
    if isinstance(instance, ReporteGenerado):
        return f'Reporte generado: {instance.get_tipo_reporte_display()}.'
    return f'{instance.__class__.__name__} creado.'


def _descripcion_edicion(instance, changed):
    if isinstance(instance, AlertaClinica):
        estado = instance.get_estado_display()
        return f'Alerta "{instance.titulo}" actualizada a estado {estado}.'
    campos = ', '.join(changed[:6])
    extra = '...' if len(changed) > 6 else ''
    return f'{instance.__class__.__name__} actualizado. Campos: {campos}{extra}.'


@receiver(user_logged_in, dispatch_uid='auditoria_user_logged_in')
def auditar_login(sender, request, user, **kwargs):
    registrar_actividad(
        usuario=user,
        request=request,
        accion='Inicio de sesion',
        tipo_accion=LogActividad.TipoAccion.LOGIN,
        modelo='CustomUser',
        modulo='Usuarios',
        objeto_id=user.pk,
        objeto_repr=getattr(user, 'nombre_completo', user.username),
        descripcion=f'Usuario {user.username} inicio sesion.',
        dedupe_seconds=0,
    )


@receiver(user_logged_out, dispatch_uid='auditoria_user_logged_out')
def auditar_logout(sender, request, user, **kwargs):
    if not user:
        return
    registrar_actividad(
        usuario=user,
        request=request,
        accion='Cierre de sesion',
        tipo_accion=LogActividad.TipoAccion.LOGOUT,
        modelo='CustomUser',
        modulo='Usuarios',
        objeto_id=user.pk,
        objeto_repr=getattr(user, 'nombre_completo', user.username),
        descripcion=f'Usuario {user.username} cerro sesion.',
        dedupe_seconds=0,
    )


@receiver(pre_save, sender=Paciente, dispatch_uid='auditoria_prev_paciente')
@receiver(pre_save, sender=CuestionarioCribado, dispatch_uid='auditoria_prev_cribado')
@receiver(pre_save, sender=ReferenciaMedica, dispatch_uid='auditoria_prev_referencia')
@receiver(pre_save, sender=SeguimientoPaciente, dispatch_uid='auditoria_prev_seguimiento')
@receiver(pre_save, sender=DocumentoMedico, dispatch_uid='auditoria_prev_documento')
@receiver(pre_save, sender=SolicitudDocumento, dispatch_uid='auditoria_prev_solicitud_documento')
@receiver(pre_save, sender=AlertaClinica, dispatch_uid='auditoria_prev_alerta')
def auditar_pre_save(sender, instance, **kwargs):
    instance._audit_previous = _get_previous(sender, instance)


@receiver(post_save, sender=Paciente, dispatch_uid='auditoria_save_paciente')
@receiver(post_save, sender=CuestionarioCribado, dispatch_uid='auditoria_save_cribado')
@receiver(post_save, sender=ReferenciaMedica, dispatch_uid='auditoria_save_referencia')
@receiver(post_save, sender=SeguimientoPaciente, dispatch_uid='auditoria_save_seguimiento')
@receiver(post_save, sender=DocumentoMedico, dispatch_uid='auditoria_save_documento')
@receiver(post_save, sender=SolicitudDocumento, dispatch_uid='auditoria_save_solicitud_documento')
def auditar_modelo_clinico(sender, instance, created, **kwargs):
    changed = _changed_fields(sender, instance)
    if not created and not changed:
        return
    tipo = LogActividad.TipoAccion.CREACION if created else LogActividad.TipoAccion.EDICION
    accion = f'Crear {sender.__name__}' if created else f'Editar {sender.__name__}'
    registrar_actividad(
        usuario=_usuario_modelo(instance),
        accion=accion,
        tipo_accion=tipo,
        modelo=sender.__name__,
        modulo=MODULOS.get(sender, sender.__name__),
        objeto_id=instance.pk,
        objeto_repr=str(instance),
        descripcion=_descripcion_creacion(instance) if created else _descripcion_edicion(instance, changed),
    )


@receiver(post_save, sender=AlertaClinica, dispatch_uid='auditoria_save_alerta')
def auditar_alerta(sender, instance, created, **kwargs):
    if created:
        return
    changed = _changed_fields(sender, instance)
    if 'estado' not in changed:
        return
    registrar_actividad(
        usuario=instance.revisado_por,
        accion='Cambio de estado de alerta clinica',
        tipo_accion=LogActividad.TipoAccion.EDICION,
        modelo='AlertaClinica',
        modulo='Alertas',
        objeto_id=instance.pk,
        objeto_repr=instance.titulo,
        descripcion=_descripcion_edicion(instance, changed),
    )


@receiver(post_save, sender=ReporteGenerado, dispatch_uid='auditoria_save_reporte')
def auditar_reporte(sender, instance, created, **kwargs):
    if not created:
        return
    registrar_actividad(
        usuario=instance.generado_por,
        accion='Generar reporte',
        tipo_accion=LogActividad.TipoAccion.REPORTE,
        modelo='ReporteGenerado',
        modulo='Reportes',
        objeto_id=instance.pk,
        objeto_repr=str(instance),
        descripcion=_descripcion_creacion(instance),
    )


@receiver(post_delete, sender=DocumentoMedico, dispatch_uid='auditoria_delete_documento')
@receiver(post_delete, sender=SolicitudDocumento, dispatch_uid='auditoria_delete_solicitud_documento')
def auditar_eliminacion_documentos(sender, instance, **kwargs):
    registrar_actividad(
        usuario=_usuario_modelo(instance),
        accion=f'Eliminar {sender.__name__}',
        tipo_accion=LogActividad.TipoAccion.ELIMINACION,
        modelo=sender.__name__,
        modulo=MODULOS.get(sender, sender.__name__),
        objeto_id=instance.pk,
        objeto_repr=str(instance),
        descripcion=f'{sender.__name__} eliminado: {instance}.',
    )
