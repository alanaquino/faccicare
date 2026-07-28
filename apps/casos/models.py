import uuid
from django.db import models
from django.conf import settings

from apps.pacientes.models import Paciente
from apps.cribado.models import CuestionarioCribado


class CasoClinico(models.Model):

    class EstadoCaso(models.TextChoices):
        ABIERTO        = 'ABIERTO',        'Abierto'
        EN_ESTUDIO     = 'EN_ESTUDIO',     'En estudio'
        EN_TRATAMIENTO = 'EN_TRATAMIENTO', 'En tratamiento'
        EN_REMISION    = 'EN_REMISION',    'En remisión'
        CERRADO        = 'CERRADO',        'Cerrado'
        ARCHIVADO      = 'ARCHIVADO',      'Archivado'

    class TipoCancer(models.TextChoices):
        LEUCEMIA       = 'LEUCEMIA',       'Leucemia'
        TUMORES_SNC    = 'TUMORES_SNC',    'Tumores del SNC'
        RETINOBLASTOMA = 'RETINOBLASTOMA', 'Retinoblastoma'
        TUMOR_WILMS    = 'TUMOR_WILMS',    'Tumor de Wilms'
        NEUROBLASTOMA  = 'NEUROBLASTOMA',  'Neuroblastoma'
        LINFOMA        = 'LINFOMA',        'Linfoma'
        SARCOMA        = 'SARCOMA',        'Sarcoma'
        OTRO           = 'OTRO',           'Otro / Por definir'

    class Prioridad(models.TextChoices):
        BAJA    = 'BAJA',    'Baja'
        MEDIA   = 'MEDIA',   'Media'
        ALTA    = 'ALTA',    'Alta'
        URGENTE = 'URGENTE', 'Urgente'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    codigo_caso = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código del caso',
        db_index=True,
        help_text='Generado automáticamente (ej. CASO-2026-0001)',
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='casos_clinicos',
        verbose_name='Paciente',
    )
    medico_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='casos_a_cargo',
        verbose_name='Médico responsable',
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='casos_creados',
        verbose_name='Creado por',
    )
    cribado_origen = models.ForeignKey(
        CuestionarioCribado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='casos_derivados',
        verbose_name='Cribado de origen',
    )
    tipo_cancer = models.CharField(
        max_length=20,
        choices=TipoCancer.choices,
        default=TipoCancer.OTRO,
        verbose_name='Tipo de cáncer',
        db_index=True,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoCaso.choices,
        default=EstadoCaso.ABIERTO,
        verbose_name='Estado del caso',
        db_index=True,
    )
    prioridad = models.CharField(
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        verbose_name='Prioridad',
        db_index=True,
    )
    titulo = models.CharField(
        max_length=250,
        verbose_name='Título del caso',
        help_text='Descripción clínica breve que identifica el caso',
    )
    resumen_clinico = models.TextField(
        verbose_name='Resumen clínico',
        help_text='Descripción del cuadro clínico, síntomas principales y hallazgos relevantes',
    )
    protocolo_tratamiento = models.TextField(
        blank=True,
        verbose_name='Protocolo de tratamiento',
        help_text='Protocolo oncológico asignado y descripción del plan terapéutico',
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones adicionales',
    )
    fecha_apertura = models.DateField(
        verbose_name='Fecha de apertura',
    )
    fecha_cierre = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de cierre',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Registrado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Caso clínico'
        verbose_name_plural = 'Casos clínicos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['paciente'],          name='caso_paciente_idx'),
            models.Index(fields=['estado'],            name='caso_estado_idx'),
            models.Index(fields=['prioridad'],         name='caso_prioridad_idx'),
            models.Index(fields=['tipo_cancer'],       name='caso_tipo_idx'),
            models.Index(fields=['fecha_apertura'],    name='caso_fecha_apertura_idx'),
            models.Index(fields=['medico_responsable'],name='caso_medico_idx'),
        ]

    def __str__(self):
        return f'{self.codigo_caso} — {self.paciente.nombre_completo}'

    def save(self, *args, **kwargs):
        if not self.codigo_caso:
            self.codigo_caso = self._generar_codigo()
        super().save(*args, **kwargs)

    def _generar_codigo(self):
        from django.utils import timezone
        year = timezone.now().year
        ultimo = (
            CasoClinico.objects
            .filter(codigo_caso__startswith=f'CASO-{year}-')
            .order_by('-codigo_caso')
            .first()
        )
        if ultimo:
            try:
                n = int(ultimo.codigo_caso.split('-')[-1]) + 1
            except ValueError:
                n = 1
        else:
            n = 1
        return f'CASO-{year}-{n:04d}'

    @property
    def estado_color(self):
        colores = {
            self.EstadoCaso.ABIERTO:        'primary',
            self.EstadoCaso.EN_ESTUDIO:     'secondary',
            self.EstadoCaso.EN_TRATAMIENTO: 'error',
            self.EstadoCaso.EN_REMISION:    'tertiary',
            self.EstadoCaso.CERRADO:        'outline',
            self.EstadoCaso.ARCHIVADO:      'outline',
        }
        return colores.get(self.estado, 'outline')

    @property
    def prioridad_color(self):
        colores = {
            self.Prioridad.URGENTE: 'error',
            self.Prioridad.ALTA:    'error',
            self.Prioridad.MEDIA:   'secondary',
            self.Prioridad.BAJA:    'tertiary',
        }
        return colores.get(self.prioridad, 'outline')

    @property
    def icono_cancer(self):
        iconos = {
            self.TipoCancer.LEUCEMIA:       'bloodtype',
            self.TipoCancer.TUMORES_SNC:    'psychology',
            self.TipoCancer.RETINOBLASTOMA: 'visibility',
            self.TipoCancer.TUMOR_WILMS:    'biotech',
            self.TipoCancer.NEUROBLASTOMA:  'hub',
            self.TipoCancer.LINFOMA:        'grain',
            self.TipoCancer.SARCOMA:        'bones',
            self.TipoCancer.OTRO:           'help_outline',
        }
        return iconos.get(self.tipo_cancer, 'medical_services')

    @property
    def dias_abierto(self):
        from django.utils import timezone
        fin = self.fecha_cierre or timezone.now().date()
        return (fin - self.fecha_apertura).days

    @property
    def total_notas(self):
        return self.notas.count()

    @property
    def esta_activo(self):
        return self.estado not in [self.EstadoCaso.CERRADO, self.EstadoCaso.ARCHIVADO]


class NotaCaso(models.Model):

    class TipoNota(models.TextChoices):
        EVOLUCION      = 'EVOLUCION',      'Evolución clínica'
        DIAGNOSTICO    = 'DIAGNOSTICO',    'Diagnóstico / Hallazgo'
        TRATAMIENTO    = 'TRATAMIENTO',    'Tratamiento / Protocolo'
        INTERCONSULTA  = 'INTERCONSULTA',  'Interconsulta'
        LABORATORIO    = 'LABORATORIO',    'Resultado de laboratorio'
        IMAGEN         = 'IMAGEN',         'Imagen médica'
        QUIRURGICO     = 'QUIRURGICO',     'Procedimiento quirúrgico'
        ALTA           = 'ALTA',           'Alta / Egreso'
        CIERRE         = 'CIERRE',         'Cierre del caso'
        OBSERVACION    = 'OBSERVACION',    'Observación general'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    caso = models.ForeignKey(
        CasoClinico,
        on_delete=models.CASCADE,
        related_name='notas',
        verbose_name='Caso clínico',
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='notas_casos',
        verbose_name='Autor',
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoNota.choices,
        default=TipoNota.EVOLUCION,
        verbose_name='Tipo de nota',
        db_index=True,
    )
    titulo = models.CharField(
        max_length=250,
        verbose_name='Título',
    )
    contenido = models.TextField(
        verbose_name='Contenido',
    )
    es_importante = models.BooleanField(
        default=False,
        verbose_name='Marcar como importante',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Registrada el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizada el')

    class Meta:
        verbose_name = 'Nota del caso'
        verbose_name_plural = 'Notas del caso'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['caso'],  name='nota_caso_idx'),
            models.Index(fields=['tipo'],  name='nota_caso_tipo_idx'),
            models.Index(fields=['autor'], name='nota_caso_autor_idx'),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.caso.codigo_caso}'

    @property
    def color(self):
        colores = {
            self.TipoNota.DIAGNOSTICO:   'primary',
            self.TipoNota.TRATAMIENTO:   'secondary',
            self.TipoNota.QUIRURGICO:    'error',
            self.TipoNota.ALTA:          'tertiary',
            self.TipoNota.CIERRE:        'outline',
            self.TipoNota.INTERCONSULTA: 'secondary',
            self.TipoNota.LABORATORIO:   'primary',
            self.TipoNota.IMAGEN:        'error',
        }
        if self.es_importante:
            return 'error'
        return colores.get(self.tipo, 'outline')

    @property
    def icono(self):
        iconos = {
            self.TipoNota.EVOLUCION:     'trending_up',
            self.TipoNota.DIAGNOSTICO:   'biotech',
            self.TipoNota.TRATAMIENTO:   'medication',
            self.TipoNota.INTERCONSULTA: 'people',
            self.TipoNota.LABORATORIO:   'science',
            self.TipoNota.IMAGEN:        'image',
            self.TipoNota.QUIRURGICO:    'surgical',
            self.TipoNota.ALTA:          'exit_to_app',
            self.TipoNota.CIERRE:        'lock',
            self.TipoNota.OBSERVACION:   'note',
        }
        return iconos.get(self.tipo, 'note')

    @property
    def fecha(self):
        meses = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
                 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
        d = self.created_at
        if not d:
            return 'Reciente'
        return f'{d.day} {meses.get(d.month, "")}, {d.year}'

    @property
    def autor_nombre(self):
        return self.autor.get_full_name() or self.autor.username
