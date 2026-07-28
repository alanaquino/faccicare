import uuid
from django.db import models
from django.conf import settings


class ReporteGenerado(models.Model):

    class TipoReporte(models.TextChoices):
        RESUMEN_MENSUAL = 'RESUMEN_MENSUAL', 'Resumen mensual'
        POR_PROVINCIA = 'POR_PROVINCIA', 'Por provincia'
        POR_DIAGNOSTICO = 'POR_DIAGNOSTICO', 'Por diagnostico'
        SEGUIMIENTO_CASOS = 'SEGUIMIENTO_CASOS', 'Seguimiento de casos'
        REFERENCIAS_MEDICAS = 'REFERENCIAS_MEDICAS', 'Referencias medicas'
        PACIENTES    = 'PACIENTES',    'Pacientes'
        REFERENCIAS  = 'REFERENCIAS',  'Referencias médicas'
        CRIBADO      = 'CRIBADO',      'Cribado oncológico'
        SEGUIMIENTO  = 'SEGUIMIENTO',  'Seguimiento clínico'
        ESTADISTICAS = 'ESTADISTICAS', 'Estadísticas generales'

    class Formato(models.TextChoices):
        PDF = 'pdf', 'PDF'
        XLSX = 'xlsx', 'Excel .xlsx'
        CSV = 'csv', 'CSV'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    generado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reportes_generados',
        verbose_name='Generado por',
    )
    tipo_reporte = models.CharField(
        max_length=30,
        choices=TipoReporte.choices,
        verbose_name='Tipo de reporte',
        db_index=True,
    )
    nombre_reporte = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Nombre del reporte',
    )
    formato = models.CharField(
        max_length=10,
        choices=Formato.choices,
        default=Formato.PDF,
        verbose_name='Formato',
        db_index=True,
    )
    codigo_documento = models.CharField(
        max_length=40,
        blank=True,
        verbose_name='Codigo del documento',
    )
    total_registros = models.PositiveIntegerField(default=0, verbose_name='Total de registros')
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name='Período desde',
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name='Período hasta',
    )
    archivo = models.FileField(
        upload_to='reportes/%Y/%m/',
        blank=True,
        verbose_name='Archivo generado',
        help_text='PDF o Excel con los datos del reporte',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Generado el')

    class Meta:
        verbose_name = 'Reporte generado'
        verbose_name_plural = 'Reportes generados'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tipo_reporte'], name='reporte_tipo_idx'),
            models.Index(fields=['formato'], name='reporte_formato_idx'),
            models.Index(fields=['generado_por'], name='reporte_usuario_idx'),
        ]

    def __str__(self):
        periodo = ''
        if self.fecha_inicio and self.fecha_fin:
            periodo = (
                f' ({self.fecha_inicio.strftime("%d/%m/%Y")} — '
                f'{self.fecha_fin.strftime("%d/%m/%Y")})'
            )
        nombre = self.nombre_reporte or self.get_tipo_reporte_display()
        return f'{nombre}{periodo}'
