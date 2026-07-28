import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class Notificacion(models.Model):

    class TipoNotificacion(models.TextChoices):
        SISTEMA = 'sistema', 'Sistema'
        REFERENCIA = 'referencia', 'Referencia'
        CITA = 'cita', 'Cita'
        SEGUIMIENTO = 'seguimiento', 'Seguimiento'
        ALERTA = 'alerta', 'Alerta'
        ALERTA_CLINICA = 'alerta_clinica', 'Alerta clinica'
        MENSAJE = 'mensaje', 'Mensaje'
        REPORTE = 'reporte', 'Reporte'
        DOCUMENTO = 'documento', 'Documento'
        PACIENTE = 'paciente', 'Paciente'
        CRIBADO = 'cribado', 'Cribado'
        MEDICAMENTO = 'medicamento', 'Medicamento'
        SINTOMAS = 'sintomas', 'Sintomas'

    class Prioridad(models.TextChoices):
        BAJA = 'baja', 'Baja'
        MEDIA = 'media', 'Media'
        ALTA = 'alta', 'Alta'
        CRITICA = 'critica', 'Critica'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones',
        verbose_name='Usuario destinatario',
    )
    tipo = models.CharField(
        max_length=30,
        choices=TipoNotificacion.choices,
        default=TipoNotificacion.SISTEMA,
        verbose_name='Tipo',
        db_index=True,
    )
    modulo = models.CharField(max_length=80, blank=True, verbose_name='Modulo relacionado', db_index=True)
    prioridad = models.CharField(
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        verbose_name='Prioridad',
        db_index=True,
    )
    titulo = models.CharField(max_length=180, verbose_name='Titulo')
    mensaje = models.TextField(verbose_name='Mensaje')
    leida = models.BooleanField(default=False, verbose_name='Leida', db_index=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de lectura')
    accion_url = models.CharField(max_length=255, blank=True, null=True, verbose_name='URL de accion')
    accion_texto = models.CharField(max_length=100, blank=True, null=True, verbose_name='Texto de accion')
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificaciones',
        verbose_name='Tipo de objeto relacionado',
    )
    objeto_id = models.CharField(max_length=80, blank=True, verbose_name='ID de objeto relacionado')
    objeto_relacionado = GenericForeignKey('content_type', 'objeto_id')
    icono_nombre = models.CharField(max_length=50, blank=True, verbose_name='Icono visual')
    clave_dedupe = models.CharField(
        max_length=180,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Clave de deduplicacion',
    )
    archivada = models.BooleanField(default=False, verbose_name='Archivada', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creada el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizada el')

    class Meta:
        verbose_name = 'Notificacion'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['usuario'], name='notif_usuario_idx'),
            models.Index(fields=['usuario', 'leida'], name='noti_user_leida_idx'),
            models.Index(fields=['usuario', 'archivada'], name='noti_user_arch_idx'),
            models.Index(fields=['tipo'], name='noti_tipo_idx'),
            models.Index(fields=['prioridad'], name='noti_prioridad_idx'),
            models.Index(fields=['created_at'], name='notif_created_at_idx'),
        ]

    def __str__(self):
        nombre = self.usuario.get_full_name() or self.usuario.username
        return f'{nombre} - {self.titulo}'

    @property
    def estado(self):
        return 'leida' if self.leida else 'no_leida'

    @property
    def icono(self):
        if self.icono_nombre:
            return self.icono_nombre
        mapping = {
            self.TipoNotificacion.ALERTA: 'warning',
            self.TipoNotificacion.ALERTA_CLINICA: 'emergency_home',
            self.TipoNotificacion.MENSAJE: 'chat_bubble',
            self.TipoNotificacion.CITA: 'calendar_today',
            self.TipoNotificacion.REFERENCIA: 'send',
            self.TipoNotificacion.SEGUIMIENTO: 'monitor_heart',
            self.TipoNotificacion.SISTEMA: 'system_update',
            self.TipoNotificacion.REPORTE: 'bar_chart',
            self.TipoNotificacion.DOCUMENTO: 'description',
            self.TipoNotificacion.PACIENTE: 'personal_injury',
            self.TipoNotificacion.CRIBADO: 'fact_check',
            self.TipoNotificacion.MEDICAMENTO: 'medication',
            self.TipoNotificacion.SINTOMAS: 'thermostat',
        }
        return mapping.get(self.tipo, 'notifications')

    @property
    def color(self):
        if self.prioridad in [self.Prioridad.CRITICA, self.Prioridad.ALTA]:
            return 'error'
        if self.tipo in [self.TipoNotificacion.ALERTA, self.TipoNotificacion.ALERTA_CLINICA, self.TipoNotificacion.SINTOMAS]:
            return 'error'
        mapping = {
            self.TipoNotificacion.MENSAJE: 'primary',
            self.TipoNotificacion.CITA: 'secondary',
            self.TipoNotificacion.REFERENCIA: 'tertiary',
            self.TipoNotificacion.SEGUIMIENTO: 'primary',
            self.TipoNotificacion.REPORTE: 'secondary',
            self.TipoNotificacion.DOCUMENTO: 'tertiary',
            self.TipoNotificacion.PACIENTE: 'primary',
            self.TipoNotificacion.CRIBADO: 'secondary',
            self.TipoNotificacion.MEDICAMENTO: 'primary',
            self.TipoNotificacion.SISTEMA: 'outline',
        }
        return mapping.get(self.tipo, 'outline')

    @property
    def tiempo(self):
        from django.contrib.humanize.templatetags.humanize import naturaltime

        return naturaltime(self.created_at)

    @property
    def resolved_accion_url(self):
        if not self.accion_url:
            return '#'
        if (
            self.accion_url.startswith('/')
            or self.accion_url.startswith('http://')
            or self.accion_url.startswith('https://')
        ):
            return self.accion_url

        from django.urls import NoReverseMatch, reverse

        try:
            return reverse(self.accion_url)
        except NoReverseMatch:
            return self.accion_url

    @property
    def abrir_url(self):
        from django.urls import reverse

        return reverse('notificaciones:abrir_notificacion', kwargs={'pk': self.pk})

    def marcar_como_leida(self, commit=True):
        if self.leida:
            return False
        self.leida = True
        self.fecha_lectura = timezone.now()
        if commit:
            self.save(update_fields=['leida', 'fecha_lectura', 'updated_at'])
        return True

    def marcar_como_no_leida(self, commit=True):
        if not self.leida:
            return False
        self.leida = False
        self.fecha_lectura = None
        if commit:
            self.save(update_fields=['leida', 'fecha_lectura', 'updated_at'])
        return True

    @classmethod
    def seed_for_user(cls, user):
        """Backwards-compatible entry point: syncs real data only."""
        cls.sync_real_notifications(user)

    @classmethod
    def sync_real_notifications(cls, user):
        if not user or not getattr(user, 'is_authenticated', False):
            return
        from .services import sincronizar_notificaciones_usuario

        sincronizar_notificaciones_usuario(user)
