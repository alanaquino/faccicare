import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class AlertaClinica(models.Model):
    class TipoAlerta(models.TextChoices):
        SINTOMAS_ALARMA = 'SINTOMAS_ALARMA', 'Sintomas de alarma'
        SOSPECHOSO_SIN_REFERENCIA = 'SOSPECHOSO_SIN_REFERENCIA', 'Sospechoso sin referencia'
        REFERENCIA_SIN_SEGUIMIENTO = 'REFERENCIA_SIN_SEGUIMIENTO', 'Referencia sin seguimiento'
        SEGUIMIENTO_PENDIENTE = 'SEGUIMIENTO_PENDIENTE', 'Seguimiento pendiente o vencido'
        ALTA_PRIORIDAD_SIN_REVISION = 'ALTA_PRIORIDAD_SIN_REVISION', 'Alta prioridad sin revision'
        DOCUMENTO_PENDIENTE = 'DOCUMENTO_PENDIENTE', 'Documento clinico pendiente'
        CASO_CRITICO = 'CASO_CRITICO', 'Caso critico'

    class Prioridad(models.TextChoices):
        BAJA = 'BAJA', 'Baja'
        MEDIA = 'MEDIA', 'Media'
        ALTA = 'ALTA', 'Alta'
        CRITICA = 'CRITICA', 'Critica'

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        REVISADA = 'REVISADA', 'Revisada'
        RESUELTA = 'RESUELTA', 'Resuelta'
        DESCARTADA = 'DESCARTADA', 'Descartada'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        'pacientes.Paciente',
        on_delete=models.CASCADE,
        related_name='alertas_clinicas',
        verbose_name='Paciente',
    )
    cribado = models.ForeignKey(
        'cribado.CuestionarioCribado',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_clinicas',
        verbose_name='Cribado relacionado',
    )
    referencia = models.ForeignKey(
        'referencias.ReferenciaMedica',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_clinicas',
        verbose_name='Referencia relacionada',
    )
    seguimiento = models.ForeignKey(
        'seguimiento.SeguimientoPaciente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_clinicas',
        verbose_name='Seguimiento relacionado',
    )
    documento = models.ForeignKey(
        'documentos.DocumentoMedico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_clinicas',
        verbose_name='Documento relacionado',
    )
    solicitud_documento = models.ForeignKey(
        'documentos.SolicitudDocumento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_clinicas',
        verbose_name='Solicitud de documento relacionada',
    )
    tipo_alerta = models.CharField(
        max_length=40,
        choices=TipoAlerta.choices,
        db_index=True,
        verbose_name='Tipo de alerta',
    )
    prioridad = models.CharField(
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        db_index=True,
        verbose_name='Nivel de prioridad',
    )
    titulo = models.CharField(max_length=180, verbose_name='Titulo')
    descripcion = models.TextField(verbose_name='Descripcion')
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
        verbose_name='Estado',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Fecha de creacion')
    fecha_limite = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='Fecha limite')
    fecha_revision = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de revision o cierre')
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas_clinicas_revisadas',
        verbose_name='Usuario que reviso o resolvio',
    )
    comentario_cierre = models.TextField(blank=True, verbose_name='Comentario u observacion de cierre')
    clave_dedupe = models.CharField(
        max_length=140,
        unique=True,
        db_index=True,
        editable=False,
        verbose_name='Clave de deduplicacion',
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizada el')

    class Meta:
        verbose_name = 'Alerta clinica'
        verbose_name_plural = 'Alertas clinicas'
        ordering = ['estado', '-prioridad', '-fecha_creacion']
        indexes = [
            models.Index(fields=['paciente', 'estado'], name='alerta_paciente_estado_idx'),
            models.Index(fields=['prioridad', 'estado'], name='alerta_prioridad_estado_idx'),
            models.Index(fields=['tipo_alerta'], name='alerta_tipo_idx'),
            models.Index(fields=['fecha_creacion'], name='alerta_fecha_idx'),
            models.Index(fields=['fecha_limite'], name='alerta_limite_idx'),
        ]

    def __str__(self):
        return f'{self.get_prioridad_display()} - {self.titulo} ({self.paciente.nombre_completo})'

    def save(self, *args, **kwargs):
        if not self.clave_dedupe:
            self.clave_dedupe = f'manual:{self.paciente_id}:{self.tipo_alerta}:{uuid.uuid4().hex[:10]}'
        super().save(*args, **kwargs)

    @property
    def abierta(self):
        return self.estado in [self.Estado.PENDIENTE, self.Estado.REVISADA]

    @property
    def esta_vencida(self):
        return bool(self.abierta and self.fecha_limite and self.fecha_limite < timezone.now())

    @property
    def dias_vencida(self):
        if not self.esta_vencida:
            return 0
        return (timezone.now().date() - self.fecha_limite.date()).days

    @property
    def color(self):
        colores = {
            self.Prioridad.CRITICA: 'error',
            self.Prioridad.ALTA: 'orange',
            self.Prioridad.MEDIA: 'amber',
            self.Prioridad.BAJA: 'primary',
        }
        return colores.get(self.prioridad, 'primary')

    @property
    def icono(self):
        iconos = {
            self.TipoAlerta.SINTOMAS_ALARMA: 'warning',
            self.TipoAlerta.SOSPECHOSO_SIN_REFERENCIA: 'send',
            self.TipoAlerta.REFERENCIA_SIN_SEGUIMIENTO: 'assignment_late',
            self.TipoAlerta.SEGUIMIENTO_PENDIENTE: 'event_busy',
            self.TipoAlerta.ALTA_PRIORIDAD_SIN_REVISION: 'priority_high',
            self.TipoAlerta.DOCUMENTO_PENDIENTE: 'description',
            self.TipoAlerta.CASO_CRITICO: 'emergency_home',
        }
        return iconos.get(self.tipo_alerta, 'notifications_active')

    @property
    def url_detalle(self):
        if self.referencia_id:
            return reverse('referencias:detalle', kwargs={'pk': self.referencia_id})
        if self.cribado_id:
            return reverse('cribado:detalle', kwargs={'pk': self.cribado_id})
        if self.documento_id:
            return reverse('documentos:detalle', kwargs={'pk': self.documento_id})
        if self.solicitud_documento_id:
            if self.solicitud_documento.documento_asociado_id:
                return reverse('documentos:detalle', kwargs={'pk': self.solicitud_documento.documento_asociado_id})
            return f'{reverse("documentos:solicitudes")}?estado={self.solicitud_documento.estado}'
        if self.paciente_id:
            if self.seguimiento_id:
                return reverse('pacientes:expediente', kwargs={'pk': self.paciente_id}) + f'?tab=evolucion#evento-{self.seguimiento_id}'
            return reverse('pacientes:expediente', kwargs={'pk': self.paciente_id})
        return reverse('alertas')
