import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.pacientes.models import Paciente


class HabitacionCasa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=80, verbose_name='Nombre / Número')
    capacidad = models.PositiveSmallIntegerField(
        default=2,
        verbose_name='Capacidad (personas)',
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Descripción',
        help_text='Planta baja, con baño privado, etc.',
    )
    activa = models.BooleanField(default=True, verbose_name='Habilitada')

    class Meta:
        verbose_name = 'Habitación'
        verbose_name_plural = 'Habitaciones'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def ocupantes_actuales(self):
        return self.estancias.filter(estado=EstanciaFamiliar.Estado.ACTIVA).count()

    @property
    def disponible(self):
        return self.activa and self.ocupantes_actuales < self.capacidad


class EstanciaFamiliar(models.Model):

    class Estado(models.TextChoices):
        ACTIVA     = 'ACTIVA',     'Activa'
        COMPLETADA = 'COMPLETADA', 'Completada'
        CANCELADA  = 'CANCELADA',  'Cancelada'

    class MotivoEstancia(models.TextChoices):
        QUIMIOTERAPIA  = 'QUIMIOTERAPIA',  'Ciclo de quimioterapia'
        CIRUGIA        = 'CIRUGIA',        'Intervención quirúrgica'
        RADIOTERAPIA   = 'RADIOTERAPIA',   'Radioterapia'
        HOSPITALIZACION = 'HOSPITALIZACION', 'Hospitalización prolongada'
        CONSULTA       = 'CONSULTA',       'Consulta / exámenes'
        OTRO           = 'OTRO',           'Otro'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='estancias',
        verbose_name='Paciente',
    )
    habitacion = models.ForeignKey(
        HabitacionCasa,
        on_delete=models.PROTECT,
        related_name='estancias',
        verbose_name='Habitación',
    )
    acompanante_nombre = models.CharField(
        max_length=150,
        verbose_name='Nombre del acompañante',
    )
    acompanante_parentesco = models.CharField(
        max_length=60,
        blank=True,
        verbose_name='Parentesco',
    )
    acompanante_telefono = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Teléfono del acompañante',
    )
    motivo = models.CharField(
        max_length=20,
        choices=MotivoEstancia.choices,
        default=MotivoEstancia.CONSULTA,
        verbose_name='Motivo de la estancia',
    )
    fecha_ingreso = models.DateField(verbose_name='Fecha de ingreso')
    fecha_egreso_prevista = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de egreso prevista',
    )
    fecha_egreso_real = models.DateField(
        null=True,
        blank=True,
        verbose_name='Fecha de egreso real',
    )
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.ACTIVA,
        verbose_name='Estado',
        db_index=True,
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='estancias_registradas',
        verbose_name='Registrado por',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Estancia familiar'
        verbose_name_plural = 'Estancias familiares'
        ordering = ['-fecha_ingreso']
        indexes = [
            models.Index(fields=['estado'], name='estancia_estado_idx'),
            models.Index(fields=['paciente'], name='estancia_pcte_idx'),
            models.Index(fields=['fecha_ingreso'], name='estancia_ingreso_idx'),
        ]

    def __str__(self):
        return f'{self.paciente.nombre_completo} — {self.habitacion} ({self.fecha_ingreso})'

    @property
    def codigo(self):
        suffix = str(self.id).replace('-', '')[:4].upper()
        return f'CASA-{self.fecha_ingreso.year}-{suffix}'

    @property
    def noches(self):
        from django.utils import timezone
        fin = self.fecha_egreso_real or (timezone.now().date() if self.estado == self.Estado.ACTIVA else None)
        if fin and self.fecha_ingreso:
            return max(0, (fin - self.fecha_ingreso).days)
        return None


class EntregaHabitacion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estancia = models.ForeignKey(
        EstanciaFamiliar,
        on_delete=models.CASCADE,
        related_name='entregas_habitacion',
        verbose_name='Estancia',
    )
    fecha_entrega = models.DateField(default=timezone.localdate, verbose_name='Fecha de entrega')
    hora_ingreso = models.TimeField(null=True, blank=True, verbose_name='Hora de ingreso')
    hora_salida = models.TimeField(null=True, blank=True, verbose_name='Hora de salida')
    entregado_por_facci = models.CharField(
        max_length=150,
        default='Encargado Administrativo FACCI',
        verbose_name='Entregado por FACCI',
    )
    recibido_por_familiar = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Recibido por familiar responsable',
    )
    entregado_por_familiar = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Entregado por familiar responsable',
    )
    recibido_por_facci = models.CharField(
        max_length=150,
        default='Encargado Administrativo FACCI',
        verbose_name='Recibido por FACCI',
    )
    observaciones = models.TextField(blank=True, verbose_name='Observaciones generales')
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entregas_habitacion_creadas',
        verbose_name='Creado por',
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Entrega de habitacion'
        verbose_name_plural = 'Entregas de habitacion'
        ordering = ['-fecha_entrega', '-fecha_creacion']
        constraints = [
            models.UniqueConstraint(fields=['estancia'], name='entrega_hab_estancia_unica'),
        ]

    def __str__(self):
        return f'Entrega {self.estancia.codigo} - {self.estancia.paciente.nombre_completo}'


class ItemEntregaHabitacion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entrega = models.ForeignKey(
        EntregaHabitacion,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Entrega',
    )
    nombre_item = models.CharField(max_length=80, verbose_name='Item')
    entregado_por_facci = models.BooleanField(default=False, verbose_name='Entregado por FACCI')
    recibido_por_familiar = models.BooleanField(default=False, verbose_name='Recibido del familiar')
    observacion = models.CharField(max_length=255, blank=True, verbose_name='Observacion')
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Item de entrega de habitacion'
        verbose_name_plural = 'Items de entrega de habitacion'
        ordering = ['orden', 'nombre_item']
        constraints = [
            models.UniqueConstraint(fields=['entrega', 'nombre_item'], name='item_entrega_hab_unico'),
        ]

    def __str__(self):
        return f'{self.nombre_item} - {self.entrega.estancia.codigo}'
