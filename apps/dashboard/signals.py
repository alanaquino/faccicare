from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.cribado.models import CuestionarioCribado
from apps.documentos.models import DocumentoMedico, SolicitudDocumento
from apps.pacientes.models import Paciente
from apps.referencias.models import ReferenciaMedica
from apps.seguimiento.models import SeguimientoPaciente

from .services import (
    generar_alertas_cribado,
    generar_alertas_documento,
    generar_alertas_paciente,
    generar_alertas_referencia,
    generar_alertas_seguimiento,
    generar_alertas_solicitud_documento,
)


@receiver(post_save, sender=CuestionarioCribado, dispatch_uid='alertas_cribado_post_save')
def crear_alertas_desde_cribado(sender, instance, **kwargs):
    generar_alertas_cribado(instance)


@receiver(post_save, sender=ReferenciaMedica, dispatch_uid='alertas_referencia_post_save')
def crear_alertas_desde_referencia(sender, instance, **kwargs):
    generar_alertas_referencia(instance)


@receiver(post_save, sender=SeguimientoPaciente, dispatch_uid='alertas_seguimiento_post_save')
def crear_alertas_desde_seguimiento(sender, instance, **kwargs):
    generar_alertas_seguimiento(instance)


@receiver(post_save, sender=DocumentoMedico, dispatch_uid='alertas_documento_post_save')
def crear_alertas_desde_documento(sender, instance, **kwargs):
    generar_alertas_documento(instance)


@receiver(post_save, sender=SolicitudDocumento, dispatch_uid='alertas_solicitud_documento_post_save')
def crear_alertas_desde_solicitud_documento(sender, instance, **kwargs):
    generar_alertas_solicitud_documento(instance)


@receiver(post_save, sender=Paciente, dispatch_uid='alertas_paciente_post_save')
def crear_alertas_desde_paciente(sender, instance, **kwargs):
    generar_alertas_paciente(instance)
