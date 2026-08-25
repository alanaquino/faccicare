import re
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.core.constants import (
    RANGOS_TENSION_ARTERIAL_PEDIATRICA,
    TEMPERATURA_FIEBRE_C,
    TEMPERATURA_HIPOTERMIA_C,
)
from apps.pacientes.models import Paciente

_TENSION_ARTERIAL_RE = re.compile(r'^\s*(\d{2,3})\s*/\s*(\d{2,3})')


class SeguimientoPaciente(models.Model):

    class FaseProtocolo(models.TextChoices):
        INDUCCION = 'INDUCCION', 'Inducción'
        CONSOLIDACION = 'CONSOLIDACION', 'Consolidación'
        MANTENIMIENTO = 'MANTENIMIENTO', 'Mantenimiento'
        VIGILANCIA = 'VIGILANCIA', 'Vigilancia'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='seguimientos',
        verbose_name='Paciente',
    )
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='seguimientos_realizados',
        verbose_name='Médico tratante',
    )
    fecha_seguimiento = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha del seguimiento',
    )
    fase_protocolo = models.CharField(
        max_length=20,
        choices=FaseProtocolo.choices,
        default=FaseProtocolo.VIGILANCIA,
        verbose_name='Fase del protocolo',
    )
    estado_clinico = models.CharField(
        max_length=200,
        verbose_name='Estado clínico actual',
        help_text='Resumen breve del estado del paciente en esta consulta',
    )
    sintomas_actuales = models.TextField(
        blank=True,
        verbose_name='Síntomas actuales',
    )
    tratamiento_actual = models.TextField(
        blank=True,
        verbose_name='Tratamiento en curso',
        help_text='Descripción del protocolo de tratamiento activo',
    )
    medicamentos = models.TextField(
        blank=True,
        verbose_name='Medicamentos indicados',
        help_text='Lista de medicamentos, dosis y frecuencia',
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones del médico',
    )
    proxima_fecha_seguimiento = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Próximo seguimiento',
    )
    medico_seguimiento = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seguimientos_agendados',
        verbose_name='Médico del seguimiento',
    )
    lugar_seguimiento = models.ForeignKey(
        'core.CentroSalud',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='seguimientos',
        verbose_name='Lugar / Centro del seguimiento',
    )
    peso_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Peso (kg)',
    )
    talla_cm = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Talla (cm)',
    )
    temperatura_c = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Temperatura (°C)',
    )
    tension_arterial = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Tensión arterial (mmHg)',
        help_text='Formato sistólica/diastólica, ej. 110/70',
    )
    requiere_hospitalizacion = models.BooleanField(
        default=False,
        verbose_name='Requiere hospitalización',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Seguimiento de paciente'
        verbose_name_plural = 'Seguimientos de pacientes'
        ordering = ['-fecha_seguimiento']
        indexes = [
            models.Index(fields=['paciente'], name='seguimiento_paciente_idx'),
            models.Index(fields=['fecha_seguimiento'], name='seguimiento_fecha_idx'),
            models.Index(fields=['requiere_hospitalizacion'], name='seguimiento_hosp_idx'),
        ]

    @property
    def imc(self):
        if self.peso_kg and self.talla_cm and self.talla_cm > 0:
            talla_m = float(self.talla_cm) / 100
            return round(float(self.peso_kg) / (talla_m ** 2), 1)
        return None

    @property
    def tension_arterial_valores(self):
        """(sistolica, diastolica) como enteros si el texto libre tiene formato NN/NN, si no None."""
        if not self.tension_arterial:
            return None
        m = _TENSION_ARTERIAL_RE.match(self.tension_arterial)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2))

    @property
    def _edad_paciente_meses(self):
        if not self.paciente_id or not self.paciente.fecha_nacimiento:
            return None
        hoy = timezone.now().date()
        birth = self.paciente.fecha_nacimiento
        return (hoy.year - birth.year) * 12 + (hoy.month - birth.month) - (1 if hoy.day < birth.day else 0)

    @property
    def alerta_temperatura(self):
        if self.temperatura_c is None:
            return None
        temp = float(self.temperatura_c)
        if temp >= TEMPERATURA_FIEBRE_C:
            return f'Temperatura elevada (fiebre): {temp}°C'
        if temp < TEMPERATURA_HIPOTERMIA_C:
            return f'Temperatura baja (hipotermia): {temp}°C'
        return None

    @property
    def alerta_tension_arterial(self):
        """Compara la TA reportada contra rangos orientativos por edad (ver apps.core.constants)."""
        valores = self.tension_arterial_valores
        if not valores:
            return None
        edad_meses = self._edad_paciente_meses
        if edad_meses is None:
            return None
        sistolica, diastolica = valores
        for edad_max, sis_min, sis_max, dia_min, dia_max, etiqueta in RANGOS_TENSION_ARTERIAL_PEDIATRICA:
            if edad_meses > edad_max:
                continue
            problemas = []
            if not (sis_min <= sistolica <= sis_max):
                problemas.append(f'sistólica {sistolica} mmHg (esperado {sis_min}-{sis_max} para {etiqueta})')
            if not (dia_min <= diastolica <= dia_max):
                problemas.append(f'diastólica {diastolica} mmHg (esperado {dia_min}-{dia_max} para {etiqueta})')
            if problemas:
                return 'Tensión arterial fuera de rango esperado: ' + '; '.join(problemas)
            return None
        return None

    @property
    def alertas_valores_atipicos(self):
        return [a for a in (self.alerta_temperatura, self.alerta_tension_arterial) if a]

    @property
    def tiene_valores_atipicos(self):
        return bool(self.alertas_valores_atipicos)

    def __str__(self):
        return (
            f'Seguimiento {self.paciente.nombre_completo} — '
            f'{self.fecha_seguimiento.strftime("%d/%m/%Y")}'
        )


class IndicacionMedica(models.Model):
    class TipoIndicacion(models.TextChoices):
        MEDICACION = 'MEDICACION', 'Medicación'
        PROTOCOLO_ACTIVO = 'PROTOCOLO_ACTIVO', 'Protocolo Activo'
        PAUTA_MEDICA = 'PAUTA_MEDICA', 'Pauta Médica Específica'
        HIDRATACION = 'HIDRATACION', 'Hidratación'
        DESCANSO = 'DESCANSO', 'Descanso'
        ALIMENTACION = 'ALIMENTACION', 'Alimentación'
        HIGIENE = 'HIGIENE', 'Higiene'
        OTRA = 'OTRA', 'Otra'

    class Prioridad(models.TextChoices):
        ALTA = 'ALTA', 'Alta'
        MEDIA = 'MEDIA', 'Media'
        BAJA = 'BAJA', 'Baja'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='indicaciones_medicas',
        verbose_name='Paciente',
    )
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='indicaciones_prescritas',
        verbose_name='Médico tratante',
    )
    tipo_indicacion = models.CharField(
        max_length=50,
        choices=TipoIndicacion.choices,
        default=TipoIndicacion.OTRA,
        verbose_name='Tipo de indicación',
    )
    titulo = models.CharField(
        max_length=200,
        verbose_name='Título de la indicación',
    )
    descripcion = models.TextField(
        verbose_name='Descripción / Instrucciones',
    )
    prioridad = models.CharField(
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.MEDIA,
        verbose_name='Nivel de prioridad',
    )
    activa = models.BooleanField(
        default=True,
        verbose_name='Activa',
    )
    visible_padre = models.BooleanField(
        default=True,
        verbose_name='Visible para padre/tutor',
        help_text='Permite mostrar esta indicación en el Portal Padres.',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Indicación médica'
        verbose_name_plural = 'Indicaciones médicas'
        ordering = ['prioridad', '-created_at']

    def __str__(self):
        return f"{self.get_tipo_indicacion_display()} - {self.titulo} ({self.paciente.nombre_completo})"

    @property
    def icono(self):
        iconos = {
            self.TipoIndicacion.MEDICACION: 'medication',
            self.TipoIndicacion.PROTOCOLO_ACTIVO: 'assignment',
            self.TipoIndicacion.PAUTA_MEDICA: 'rate_review',
            self.TipoIndicacion.HIDRATACION: 'water_drop',
            self.TipoIndicacion.DESCANSO: 'bedtime',
            self.TipoIndicacion.ALIMENTACION: 'restaurant',
            self.TipoIndicacion.HIGIENE: 'clean_hands',
            self.TipoIndicacion.OTRA: 'info',
        }
        return iconos.get(self.tipo_indicacion, 'info')

    @property
    def color(self):
        colores = {
            self.Prioridad.ALTA: 'error',
            self.Prioridad.MEDIA: 'primary',
            self.Prioridad.BAJA: 'secondary',
        }
        return colores.get(self.prioridad, 'primary')
