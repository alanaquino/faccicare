import uuid
from django.db import models
from django.conf import settings

from apps.pacientes.models import Paciente
from apps.cribado.models import CuestionarioCribado
from apps.alojamiento.models import HabitacionCasa


class ReferenciaMedica(models.Model):

    class Prioridad(models.TextChoices):
        BAJA    = 'BAJA',    'Baja'
        MEDIA   = 'MEDIA',   'Media'
        ALTA    = 'ALTA',    'Alta'
        URGENTE = 'URGENTE', 'Urgente'

    class EstadoReferencia(models.TextChoices):
        PENDIENTE  = 'PENDIENTE',  'Pendiente'
        ACEPTADA   = 'ACEPTADA',   'Aceptada'
        EN_PROCESO = 'EN_PROCESO', 'En proceso'
        COMPLETADA = 'COMPLETADA', 'Completada'
        CANCELADA  = 'CANCELADA',  'Cancelada'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='referencias',
        verbose_name='Paciente',
    )
    cuestionario = models.ForeignKey(
        CuestionarioCribado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referencias_generadas',
        verbose_name='Cribado de origen',
        help_text='Cuestionario que motivó esta referencia',
    )
    medico_referente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='referencias_emitidas',
        verbose_name='Médico referente',
    )
    especialista_destino = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referencias_recibidas',
        verbose_name='Especialista destino',
        help_text='Especialista dentro del sistema que recibirá al paciente',
    )
    hospital_destino = models.ForeignKey(
        'core.CentroSalud',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='referencias_destino',
        verbose_name='Hospital / Centro de destino',
    )
    motivo_referencia = models.TextField(
        verbose_name='Motivo de referencia',
        help_text='Descripción clínica que justifica la referencia',
    )
    prioridad = models.CharField(
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        verbose_name='Prioridad',
        db_index=True,
    )
    estado = models.CharField(
        max_length=15,
        choices=EstadoReferencia.choices,
        default=EstadoReferencia.PENDIENTE,
        verbose_name='Estado',
        db_index=True,
    )
    fecha_referencia = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de referencia',
        db_index=True,
    )
    fecha_cita = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de cita agendada',
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones adicionales',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Referencia médica'
        verbose_name_plural = 'Referencias médicas'
        ordering = ['-fecha_referencia']
        indexes = [
            models.Index(fields=['estado'], name='referencia_estado_idx'),
            models.Index(fields=['prioridad'], name='referencia_prioridad_idx'),
            models.Index(fields=['paciente'], name='referencia_paciente_idx'),
        ]

    def __str__(self):
        return (
            f'Ref. {self.paciente.nombre_completo} → {self.hospital_destino or "sin destino"} '
            f'[{self.get_prioridad_display()}]'
        )

    @property
    def codigo(self):
        """ID amigable: REF-AAAA-XXXX (año + primeros 4 hex del UUID)."""
        year = self.fecha_referencia.year if self.fecha_referencia else 'XXXX'
        suffix = str(self.id).replace('-', '')[:4].upper()
        return f"REF-{year}-{suffix}"

    @property
    def es_urgente(self):
        return self.prioridad == self.Prioridad.URGENTE

    @property
    def edad(self):
        return self.paciente.edad

    @property
    def fecha(self):
        meses = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
        d = self.fecha_referencia
        if not d:
            return "Reciente"
        return f"{d.day} {meses.get(d.month, '')}, {d.year}"

    @property
    def hospital(self):
        return self.hospital_destino.nombre if self.hospital_destino else ''

    @property
    def especialidad(self):
        return self.especialista_destino.especialidad if self.especialista_destino and self.especialista_destino.especialidad else 'Oncología Pediátrica'

    @property
    def medico_origen(self):
        return self.medico_referente.nombre_completo if self.medico_referente else 'Dr. Martínez'

    @property
    def medico_destino(self):
        return self.especialista_destino.nombre_completo if self.especialista_destino else 'Dra. Elena Vargas'

    @property
    def estado_color(self):
        if self.prioridad in [self.Prioridad.URGENTE, self.Prioridad.ALTA]:
            return 'error'
        elif self.estado == self.EstadoReferencia.PENDIENTE:
            return 'secondary'
        return 'tertiary'

    @property
    def motivo(self):
        return self.motivo_referencia

    @property
    def tiene_contrarreferencia(self):
        return hasattr(self, 'contrarreferencia')


class Contrarreferencia(models.Model):

    class ResultadoAtencion(models.TextChoices):
        CONFIRMADO_SEGUIMIENTO = 'CONFIRMADO_SEGUIMIENTO', 'Diagnóstico confirmado — en seguimiento FACCI'
        TRATAMIENTO_INICIADO   = 'TRATAMIENTO_INICIADO',   'Tratamiento iniciado'
        DERIVADO_OTRO_NIVEL    = 'DERIVADO_OTRO_NIVEL',    'Derivado a otro nivel de atención'
        ALTA_MEDICA            = 'ALTA_MEDICA',            'Alta médica — descartado'
        NO_PRESENTADO          = 'NO_PRESENTADO',          'Paciente no se presentó'
        FALLECIDO              = 'FALLECIDO',              'Paciente fallecido'

    class Estadio(models.TextChoices):
        I   = 'I',   'Estadio I'
        II  = 'II',  'Estadio II'
        III = 'III', 'Estadio III'
        IV  = 'IV',  'Estadio IV'
        NE  = 'NE',  'No estadificado / N/A'

    class TipoCancer(models.TextChoices):
        LEUCEMIA       = 'LEUCEMIA',       'Leucemia'
        TUMORES_SNC    = 'TUMORES_SNC',    'Tumores del SNC'
        RETINOBLASTOMA = 'RETINOBLASTOMA', 'Retinoblastoma'
        TUMOR_WILMS    = 'TUMOR_WILMS',    'Tumor de Wilms'
        NEUROBLASTOMA  = 'NEUROBLASTOMA',  'Neuroblastoma'
        LINFOMA        = 'LINFOMA',        'Linfoma'
        SARCOMA        = 'SARCOMA',        'Sarcoma'
        DESCARTADO     = 'DESCARTADO',     'Sospecha descartada'
        OTRO           = 'OTRO',           'Otro / Por definir'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    referencia = models.OneToOneField(
        ReferenciaMedica,
        on_delete=models.CASCADE,
        related_name='contrarreferencia',
        verbose_name='Referencia de origen',
    )
    medico_contrarreferente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='contrareferencias_emitidas',
        verbose_name='Médico que emite contrarreferencia',
    )
    fecha_atencion = models.DateField(
        verbose_name='Fecha de atención',
        help_text='Fecha en que el paciente fue atendido en el centro destino',
    )
    diagnostico = models.TextField(
        verbose_name='Diagnóstico establecido',
        help_text='Diagnóstico clínico o histopatológico confirmado',
    )
    tipo_cancer = models.CharField(
        max_length=20,
        choices=TipoCancer.choices,
        verbose_name='Tipo de cáncer confirmado',
        blank=True,
    )
    estadio = models.CharField(
        max_length=3,
        choices=Estadio.choices,
        default=Estadio.NE,
        verbose_name='Estadio clínico',
    )
    tratamiento_realizado = models.TextField(
        blank=True,
        verbose_name='Tratamiento realizado / indicado',
        help_text='Cirugía, quimioterapia, radioterapia, etc.',
    )
    estudios_realizados = models.TextField(
        blank=True,
        verbose_name='Estudios y/o imágenes realizadas',
        help_text='Laboratorios, radiografías, TAC, RMN u otros estudios efectuados',
    )
    medicamentos_indicados = models.TextField(
        blank=True,
        verbose_name='Medicamentos indicados',
        help_text='Fármacos prescritos con dosis y duración',
    )
    resultado_atencion = models.CharField(
        max_length=30,
        choices=ResultadoAtencion.choices,
        verbose_name='Resultado de la atención',
        db_index=True,
    )
    recomendaciones = models.TextField(
        blank=True,
        verbose_name='Recomendaciones al médico referente',
        help_text='Indicaciones de seguimiento para el centro de origen',
    )
    requiere_seguimiento_facci = models.BooleanField(
        default=True,
        verbose_name='Requiere seguimiento en FACCI',
    )
    proxima_cita = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha próxima cita',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contrarreferencia'
        verbose_name_plural = 'Contrareferencias'
        ordering = ['-created_at']

    def __str__(self):
        return f'Contra-ref. {self.referencia.codigo} — {self.get_resultado_atencion_display()}'

    @property
    def codigo(self):
        year = self.created_at.year if self.created_at else 'XXXX'
        suffix = str(self.id).replace('-', '')[:4].upper()
        return f"CONTRA-{year}-{suffix}"


class ReferenciaIngresoCasaFACCI(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        APROBADA = 'APROBADA', 'Aprobada'
        INGRESADO = 'INGRESADO', 'Ingresado'
        CANCELADA = 'CANCELADA', 'Cancelada'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='ingresos_casa_facci',
        verbose_name='Paciente',
    )
    referencia_medica = models.ForeignKey(
        ReferenciaMedica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos_casa_facci',
        verbose_name='Referencia medica',
    )
    centro_origen = models.ForeignKey(
        'core.CentroSalud',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos_origen',
        verbose_name='Centro de origen',
    )
    hospital_destino = models.ForeignKey(
        'core.CentroSalud',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos_destino',
        verbose_name='Hospital / destino',
    )
    motivo_ingreso = models.TextField(verbose_name='Motivo de ingreso')
    fecha_entrada = models.DateField(verbose_name='Fecha de entrada')
    fecha_salida = models.DateField(null=True, blank=True, verbose_name='Fecha de salida')
    tiempo_estadia = models.CharField(max_length=80, blank=True, verbose_name='Tiempo estimado de estadia')
    habitacion = models.ForeignKey(
        HabitacionCasa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referencias_ingreso',
        verbose_name='Habitacion asignada',
    )
    responsable_paciente = models.CharField(max_length=150, blank=True, verbose_name='Responsable del paciente')
    parentesco_responsable = models.CharField(max_length=60, blank=True, verbose_name='Parentesco')
    cedula_responsable = models.CharField(max_length=20, blank=True, verbose_name='Cedula')
    telefono_responsable = models.CharField(max_length=30, blank=True, verbose_name='Telefono')
    celular_responsable = models.CharField(max_length=30, blank=True, verbose_name='Celular')
    direccion_responsable = models.TextField(blank=True, verbose_name='Direccion')
    ocupacion_responsable = models.CharField(max_length=100, blank=True, verbose_name='Ocupacion')
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
        verbose_name='Estado',
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ingresos_casa_facci_creados',
        verbose_name='Creado por',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Referencia ingreso Casa FACCI'
        verbose_name_plural = 'Referencias ingreso Casa FACCI'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['paciente'], name='ingreso_casa_paciente_idx'),
            models.Index(fields=['estado'], name='ingreso_casa_estado_idx'),
            models.Index(fields=['fecha_entrada'], name='ingreso_casa_entrada_idx'),
        ]

    def __str__(self):
        return f'Ingreso Casa FACCI - {self.paciente.nombre_completo}'

    @property
    def codigo(self):
        year = self.fecha_creacion.year if self.fecha_creacion else 'XXXX'
        suffix = str(self.id).replace('-', '')[:4].upper()
        return f"CASA-FACCI-{year}-{suffix}"
