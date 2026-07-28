import uuid

from django.conf import settings
from django.db import models

from apps.pacientes.models import Paciente


class CuestionarioCribado(models.Model):
    CAMPOS_SINTOMAS = (
        'fiebre_persistente',
        'perdida_peso',
        'dolor_huesos',
        'palidez',
        'fatiga',
        'moretones',
        'sangrado',
        'ganglios',
        'infecciones_recurrentes',
        'dolor_cabeza',
        'vomitos',
        'masa_abdominal',
        'leucocoria',
    )
    CAMPOS_ALARMA_MAYOR = (
        'dolor_cabeza',
        'vomitos',
        'masa_abdominal',
        'leucocoria',
    )

    class TipoCancerSospechado(models.TextChoices):
        LEUCEMIA       = 'LEUCEMIA',       'Leucemia'
        TUMORES_SNC    = 'TUMORES_SNC',    'Tumores del SNC'
        RETINOBLASTOMA = 'RETINOBLASTOMA', 'Retinoblastoma'
        TUMOR_WILMS    = 'TUMOR_WILMS',    'Tumor de Wilms'
        NEUROBLASTOMA  = 'NEUROBLASTOMA',  'Neuroblastoma'
        LINFOMA        = 'LINFOMA',        'Linfoma'
        SARCOMA        = 'SARCOMA',        'Sarcoma'
        SIN_DEFINIR    = 'SIN_DEFINIR',    'Sin definir / General'

    class NivelRiesgo(models.TextChoices):
        BAJO = 'BAJO', 'Riesgo bajo'
        MEDIO = 'MEDIO', 'Riesgo moderado'
        ALTO = 'ALTO', 'Alerta roja - riesgo alto'

    class Resultado(models.TextChoices):
        SIN_SOSPECHA = 'SIN_SOSPECHA', 'Sin sospecha'
        SOSPECHA_MODERADA = 'SOSPECHA_MODERADA', 'Sospecha moderada'
        SOSPECHA_ALTA = 'SOSPECHA_ALTA', 'Sospecha alta'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='cribados',
        verbose_name='Paciente',
    )
    medico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cribados_realizados',
        verbose_name='Medico evaluador',
    )
    fecha_evaluacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de evaluacion')

    fiebre_persistente = models.BooleanField(
        default=False,
        verbose_name='Fiebre persistente (>2 semanas)',
        help_text='Temperatura >38 C sin causa aparente por mas de 2 semanas',
    )
    perdida_peso = models.BooleanField(default=False, verbose_name='Perdida de peso inexplicable')
    dolor_huesos = models.BooleanField(default=False, verbose_name='Dolor en huesos o articulaciones')
    palidez = models.BooleanField(default=False, verbose_name='Palidez marcada')
    fatiga = models.BooleanField(default=False, verbose_name='Fatiga o cansancio extremo')

    moretones = models.BooleanField(default=False, verbose_name='Moretones sin causa aparente')
    sangrado = models.BooleanField(
        default=False,
        verbose_name='Sangrado espontaneo',
        help_text='Encias, nariz u otras zonas sin traumatismo',
    )
    ganglios = models.BooleanField(
        default=False,
        verbose_name='Ganglios inflamados',
        help_text='Linfadenopatia cervical, axilar o inguinal',
    )
    infecciones_recurrentes = models.BooleanField(default=False, verbose_name='Infecciones recurrentes')

    dolor_cabeza = models.BooleanField(default=False, verbose_name='Dolor de cabeza persistente')
    vomitos = models.BooleanField(default=False, verbose_name='Vomitos matutinos sin causa gastrointestinal')
    masa_abdominal = models.BooleanField(default=False, verbose_name='Masa abdominal palpable')

    leucocoria = models.BooleanField(
        default=False,
        verbose_name='Leucocoria / reflejo ocular blanquecino',
        help_text='Pupila blanquecina o reflejo rojo ausente en fotografías — signo principal de retinoblastoma',
    )

    tipo_cancer_sospechado = models.CharField(
        max_length=20,
        choices=TipoCancerSospechado.choices,
        blank=True,
        verbose_name='Tipo de cáncer sospechado',
        help_text='Tipo de cáncer que el médico sospecha según el cuadro clínico',
        db_index=True,
    )

    observaciones = models.TextField(blank=True, verbose_name='Observaciones clinicas')
    nivel_riesgo = models.CharField(
        max_length=10,
        choices=NivelRiesgo.choices,
        default=NivelRiesgo.BAJO,
        verbose_name='Nivel de riesgo',
        db_index=True,
    )
    resultado = models.CharField(
        max_length=25,
        choices=Resultado.choices,
        default=Resultado.SIN_SOSPECHA,
        verbose_name='Resultado del cribado',
    )
    requiere_referencia = models.BooleanField(default=False, verbose_name='Requiere referencia a especialista')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Cuestionario de cribado'
        verbose_name_plural = 'Cuestionarios de cribado'
        ordering = ['-fecha_evaluacion']
        indexes = [
            models.Index(fields=['paciente'], name='cribado_paciente_idx'),
            models.Index(fields=['nivel_riesgo'], name='cribado_nivel_idx'),
            models.Index(fields=['fecha_evaluacion'], name='cribado_fecha_idx'),
            models.Index(fields=['requiere_referencia'], name='cribado_referencia_idx'),
            models.Index(fields=['tipo_cancer_sospechado'], name='cribado_tipo_cancer_idx'),
        ]

    def __str__(self):
        fecha = self.fecha_evaluacion.strftime('%d/%m/%Y') if self.fecha_evaluacion else 'sin fecha'
        return f'Cribado {self.paciente.nombre_completo} - {self.get_nivel_riesgo_display()} ({fecha})'

    @property
    def puntaje_total(self):
        return sum(1 for campo in self.CAMPOS_SINTOMAS if getattr(self, campo))

    @property
    def tiene_alarma_mayor(self):
        return any(getattr(self, campo) for campo in self.CAMPOS_ALARMA_MAYOR)

    def calcular_resultado(self):
        puntaje = self.puntaje_total

        if self.tiene_alarma_mayor or puntaje >= 6:
            self.nivel_riesgo = self.NivelRiesgo.ALTO
            self.resultado = self.Resultado.SOSPECHA_ALTA
            self.requiere_referencia = True
        elif puntaje >= 3:
            self.nivel_riesgo = self.NivelRiesgo.MEDIO
            self.resultado = self.Resultado.SOSPECHA_MODERADA
            self.requiere_referencia = False
        else:
            self.nivel_riesgo = self.NivelRiesgo.BAJO
            self.resultado = self.Resultado.SIN_SOSPECHA
            self.requiere_referencia = False

    def save(self, *args, **kwargs):
        self.calcular_resultado()
        super().save(*args, **kwargs)
