import uuid
import os
from django.db import models
from django.conf import settings

from apps.pacientes.models import Paciente


class DocumentoMedico(models.Model):

    class TipoDocumento(models.TextChoices):
        HEMOGRAMA      = 'HEMOGRAMA',      'Hemograma'
        ANALITICA      = 'ANALITICA',      'Analítica'
        RADIOGRAFIA    = 'RADIOGRAFIA',    'Radiografía'
        SONOGRAFIA     = 'SONOGRAFIA',     'Sonografía'
        RESONANCIA     = 'RESONANCIA',     'Resonancia'
        TOMOGRAFIA     = 'TOMOGRAFIA',     'Tomografía'
        BIOPSIA        = 'BIOPSIA',        'Biopsia'
        RECETA         = 'RECETA',         'Receta médica'
        INFORME_MEDICO = 'INFORME_MEDICO', 'Informe médico'
        REFERIMIENTO   = 'REFERIMIENTO',   'Referimiento'
        OTRO           = 'OTRO',           'Otro'
        # Keep old ones for back-compatibility with seeds
        LABORATORIO    = 'LABORATORIO',    'Laboratorio'

    class EstadoDocumento(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        REVISADO  = 'REVISADO',  'Revisado'
        CORRECCION = 'CORRECCION', 'Requiere corrección'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name='Paciente',
    )
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='documentos_subidos',
        verbose_name='Subido por',
    )
    tipo_documento = models.CharField(
        max_length=20,
        choices=TipoDocumento.choices,
        verbose_name='Tipo de documento',
        db_index=True,
    )
    archivo = models.FileField(
        upload_to='documentos/%Y/%m/',
        verbose_name='Archivo',
        help_text='PDF, imagen o documento médico',
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
        help_text='Descripción breve del contenido del documento',
    )
    fecha_documento = models.DateField(
        verbose_name='Fecha del documento',
        help_text='Fecha en que fue emitido el documento',
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoDocumento.choices,
        default=EstadoDocumento.PENDIENTE,
        verbose_name='Estado',
        db_index=True,
    )
    visible_padre = models.BooleanField(
        default=False,
        verbose_name='Visible para padre/tutor',
        help_text='Permite consultar este documento desde el Portal Padres.',
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Subido el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Documento médico'
        verbose_name_plural = 'Documentos médicos'
        ordering = ['-fecha_documento']
        indexes = [
            models.Index(fields=['paciente'], name='documento_paciente_idx'),
            models.Index(fields=['tipo_documento'], name='documento_tipo_idx'),
            models.Index(fields=['fecha_documento'], name='documento_fecha_idx'),
        ]

    def __str__(self):
        return f"{self.paciente.nombre_completo} — {self.get_tipo_documento_display()}"

    @property
    def nombre_archivo(self):
        return os.path.basename(self.archivo.name) if self.archivo else ''

    @property
    def extension(self):
        _, ext = os.path.splitext(self.nombre_archivo)
        return ext.lower().lstrip('.')

    @property
    def nombre(self):
        return self.nombre_archivo or "Documento.pdf"

    @property
    def tipo(self):
        if self.tipo_documento == self.TipoDocumento.LABORATORIO:
            return "Laboratorio"
        elif self.tipo_documento in [self.TipoDocumento.RADIOGRAFIA, self.TipoDocumento.SONOGRAFIA, self.TipoDocumento.RESONANCIA, self.TipoDocumento.TOMOGRAFIA]:
            return "Imagen Médica"
        return self.get_tipo_documento_display()

    @property
    def fecha(self):
        meses = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
        d = self.fecha_documento
        if not d:
            return "Reciente"
        return f"{d.day} {meses.get(d.month, '')}, {d.year}"

    @property
    def tamano(self):
        try:
            size = self.archivo.size
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            return f"{size / (1024 * 1024):.1f} MB"
        except:
            return "0.8 MB"

    @property
    def icono(self):
        t = self.tipo_documento
        if t in [self.TipoDocumento.HEMOGRAMA, self.TipoDocumento.ANALITICA, self.TipoDocumento.LABORATORIO]:
            return "science"
        elif t in [self.TipoDocumento.RADIOGRAFIA, self.TipoDocumento.SONOGRAFIA, self.TipoDocumento.RESONANCIA, self.TipoDocumento.TOMOGRAFIA]:
            return "image"
        elif t == self.TipoDocumento.BIOPSIA:
            return "biotech"
        elif t == self.TipoDocumento.RECETA:
            return "medication"
        elif t in [self.TipoDocumento.INFORME_MEDICO, self.TipoDocumento.REFERIMIENTO]:
            return "description"
        return "assignment"

    @property
    def color(self):
        t = self.tipo_documento
        if t in [self.TipoDocumento.RADIOGRAFIA, self.TipoDocumento.SONOGRAFIA, self.TipoDocumento.RESONANCIA, self.TipoDocumento.TOMOGRAFIA]:
            return 'error'
        elif t in [self.TipoDocumento.HEMOGRAMA, self.TipoDocumento.ANALITICA, self.TipoDocumento.LABORATORIO]:
            return 'primary'
        elif t in [self.TipoDocumento.INFORME_MEDICO, self.TipoDocumento.REFERIMIENTO, self.TipoDocumento.BIOPSIA]:
            return 'secondary'
        return 'outline'


class SolicitudDocumento(models.Model):

    class EstadoSolicitud(models.TextChoices):
        PENDIENTE  = 'PENDIENTE',  'Pendiente'
        SUBIDO     = 'SUBIDO',     'Subido'
        REVISADO   = 'REVISADO',   'Revisado'
        CORRECCION = 'CORRECCION', 'Requiere corrección'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='solicitudes_documento',
        verbose_name='Paciente',
    )
    medico_solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='solicitudes_documento_creadas',
        verbose_name='Médico Solicitante',
    )
    titulo = models.CharField(
        max_length=150,
        verbose_name='Estudio Solicitado',
        help_text='Ej: Hemograma completo y plaquetas',
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name='Detalles / Indicaciones',
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoSolicitud.choices,
        default=EstadoSolicitud.PENDIENTE,
        verbose_name='Estado',
        db_index=True,
    )
    documento_asociado = models.OneToOneField(
        DocumentoMedico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitud_relacionada',
        verbose_name='Documento Asociado',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Solicitado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Solicitud de documento'
        verbose_name_plural = 'Solicitudes de documentos'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.paciente.nombre_completo} — {self.titulo} ({self.get_estado_display()})"
