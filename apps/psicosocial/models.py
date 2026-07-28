import uuid

from django.db import models
from django.utils import timezone


class EvaluacionPsicosocial(models.Model):

    # ── Choices ──────────────────────────────────────────────────────────────
    class IngresoMensual(models.TextChoices):
        NINGUNO = 'NINGUNO', 'Sin ingresos'
        BAJO = 'BAJO', 'Menos de RD$8,000/mes'
        MEDIO = 'MEDIO', 'RD$8,000 – RD$20,000/mes'
        SUFICIENTE = 'SUFICIENTE', 'Más de RD$20,000/mes'

    class Dificultad(models.TextChoices):
        NINGUNA = 'NINGUNA', 'Ninguna'
        MODERADA = 'MODERADA', 'Moderada'
        SEVERA = 'SEVERA', 'Severa'

    class CondicionVivienda(models.TextChoices):
        ADECUADA = 'ADECUADA', 'Adecuada'
        REGULAR = 'REGULAR', 'Regular'
        PRECARIA = 'PRECARIA', 'Precaria'

    class TipoVivienda(models.TextChoices):
        PROPIA = 'PROPIA', 'Propia'
        ALQUILADA = 'ALQUILADA', 'Alquilada'
        PRESTADA = 'PRESTADA', 'Prestada / Cedida'
        OTRO = 'OTRO', 'Otro'

    class Parentesco(models.TextChoices):
        MADRE = 'MADRE', 'Madre'
        PADRE = 'PADRE', 'Padre'
        ABUELO_A = 'ABUELO_A', 'Abuelo/a'
        TIO_A = 'TIO_A', 'Tío/a'
        HERMANO_A = 'HERMANO_A', 'Hermano/a mayor'
        OTRO = 'OTRO', 'Otro'

    class ApoyoFamiliar(models.TextChoices):
        BUENO = 'BUENO', 'Bueno'
        REGULAR = 'REGULAR', 'Regular'
        LIMITADO = 'LIMITADO', 'Limitado'
        NINGUNO = 'NINGUNO', 'Sin apoyo'

    class EstadoEmocional(models.TextChoices):
        ESTABLE = 'ESTABLE', 'Estable'
        VULNERABLE = 'VULNERABLE', 'Vulnerable / En riesgo'
        EN_CRISIS = 'EN_CRISIS', 'En crisis'

    class ImpactoEmocional(models.TextChoices):
        LEVE = 'LEVE', 'Leve'
        MODERADO = 'MODERADO', 'Moderado'
        SEVERO = 'SEVERO', 'Severo'

    class NivelRiesgo(models.TextChoices):
        BAJO = 'BAJO', 'Bajo'
        MEDIO = 'MEDIO', 'Moderado'
        ALTO = 'ALTO', 'Alto'
        CRITICO = 'CRITICO', 'Crítico'

    # ── Identificación ────────────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        'pacientes.Paciente', on_delete=models.CASCADE,
        related_name='evaluaciones_psicosociales',
    )
    evaluador = models.ForeignKey(
        'auth_app.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='evaluaciones_psicosociales_realizadas',
    )
    fecha_evaluacion = models.DateTimeField(default=timezone.now, db_index=True)

    # ── Datos del cuidador (informativos) ─────────────────────────────────────
    cuidador_principal_nombre = models.CharField(max_length=150, blank=True)
    parentesco_cuidador = models.CharField(
        max_length=20, choices=Parentesco.choices, blank=True,
    )
    personas_en_hogar = models.PositiveSmallIntegerField(
        default=1, help_text='Número total de personas que viven en el hogar',
    )
    tipo_vivienda = models.CharField(
        max_length=20, choices=TipoVivienda.choices, blank=True,
    )

    # ── Sección 1: Situación económica (max 9 pts) ────────────────────────────
    ingreso_mensual = models.CharField(
        max_length=20, choices=IngresoMensual.choices,
        default=IngresoMensual.MEDIO,
        verbose_name='Ingreso familiar mensual',
    )
    tiene_seguro_medico = models.BooleanField(
        default=True,
        verbose_name='Tiene seguro médico (SFS, ARS o SENASA)',
    )
    dificultad_medicamentos = models.CharField(
        max_length=20, choices=Dificultad.choices,
        default=Dificultad.NINGUNA,
        verbose_name='Dificultad para costear medicamentos',
    )
    dificultad_transporte = models.CharField(
        max_length=20, choices=Dificultad.choices,
        default=Dificultad.NINGUNA,
        verbose_name='Dificultad para trasladarse al hospital',
    )

    # ── Sección 2: Condiciones del hogar (max 5 pts) ──────────────────────────
    condicion_vivienda = models.CharField(
        max_length=20, choices=CondicionVivienda.choices,
        default=CondicionVivienda.ADECUADA,
        verbose_name='Condición general de la vivienda',
    )
    hacinamiento = models.BooleanField(
        default=False,
        verbose_name='Existe hacinamiento (más de 3 personas por habitación)',
    )
    servicios_basicos_ausentes = models.BooleanField(
        default=False,
        verbose_name='Faltan servicios básicos (agua potable, luz, saneamiento)',
    )

    # ── Sección 3: Red de apoyo social (max 4 pts) ────────────────────────────
    apoyo_familiar = models.CharField(
        max_length=20, choices=ApoyoFamiliar.choices,
        default=ApoyoFamiliar.BUENO,
        verbose_name='Red de apoyo familiar',
    )
    cuidador_es_unico = models.BooleanField(
        default=False,
        verbose_name='El cuidador es el único responsable (sin red de relevo)',
    )

    # ── Sección 4: Bienestar del cuidador (max 3 pts) ─────────────────────────
    estado_emocional_cuidador = models.CharField(
        max_length=20, choices=EstadoEmocional.choices,
        default=EstadoEmocional.ESTABLE,
        verbose_name='Estado emocional del cuidador principal',
    )
    cuidador_perdio_trabajo = models.BooleanField(
        default=False,
        verbose_name='El cuidador perdió o abandonó su empleo por el cuidado',
    )
    cuidador_requiere_apoyo_psicologico = models.BooleanField(
        default=False,
        verbose_name='El cuidador requiere apoyo psicológico',
    )

    # ── Sección 5: Impacto en el paciente (max 3 pts) ─────────────────────────
    nino_en_edad_escolar = models.BooleanField(
        default=True,
        verbose_name='El paciente está en edad escolar (3–18 años)',
    )
    abandono_escolar = models.BooleanField(
        default=False,
        verbose_name='Ha abandonado o interrumpido la escuela por la enfermedad',
    )
    impacto_emocional_paciente = models.CharField(
        max_length=20, choices=ImpactoEmocional.choices,
        default=ImpactoEmocional.LEVE,
        verbose_name='Impacto emocional observable en el paciente',
    )

    # ── Resultados calculados ─────────────────────────────────────────────────
    puntaje_total = models.PositiveSmallIntegerField(default=0, db_index=True)
    nivel_riesgo = models.CharField(
        max_length=10, choices=NivelRiesgo.choices,
        default=NivelRiesgo.BAJO, db_index=True,
    )

    # ── Plan de intervención ──────────────────────────────────────────────────
    necesidades_identificadas = models.TextField(blank=True)
    acciones_recomendadas = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)
    requiere_seguimiento_social = models.BooleanField(default=False)
    proxima_evaluacion = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_evaluacion']
        indexes = [
            models.Index(fields=['paciente', 'fecha_evaluacion'], name='psico_pcte_fecha_idx'),
        ]
        verbose_name = 'Evaluación psicosocial'
        verbose_name_plural = 'Evaluaciones psicosociales'

    def __str__(self):
        return f"Evaluación psicosocial — {self.paciente} ({self.fecha_evaluacion:%d/%m/%Y})"

    @property
    def codigo(self):
        year = self.created_at.year if self.created_at else timezone.now().year
        seq = str(self.pk)[-4:].upper()
        return f"PSI-{year}-{seq}"

    # ── Scoring ───────────────────────────────────────────────────────────────
    _SCORE_INGRESO = {'NINGUNO': 3, 'BAJO': 2, 'MEDIO': 1, 'SUFICIENTE': 0}
    _SCORE_DIFICULTAD = {'NINGUNA': 0, 'MODERADA': 1, 'SEVERA': 2}
    _SCORE_CONDICION = {'ADECUADA': 0, 'REGULAR': 1, 'PRECARIA': 2}
    _SCORE_APOYO = {'BUENO': 0, 'REGULAR': 1, 'LIMITADO': 2, 'NINGUNO': 3}
    _SCORE_EMOCIONAL = {'ESTABLE': 0, 'VULNERABLE': 1, 'EN_CRISIS': 2}
    _SCORE_IMPACTO = {'LEVE': 0, 'MODERADO': 1, 'SEVERO': 2}

    def calcular_puntaje(self):
        s = 0
        s += self._SCORE_INGRESO.get(self.ingreso_mensual, 0)
        s += 2 if not self.tiene_seguro_medico else 0
        s += self._SCORE_DIFICULTAD.get(self.dificultad_medicamentos, 0)
        s += self._SCORE_DIFICULTAD.get(self.dificultad_transporte, 0)
        s += self._SCORE_CONDICION.get(self.condicion_vivienda, 0)
        s += 1 if self.hacinamiento else 0
        s += 2 if self.servicios_basicos_ausentes else 0
        s += self._SCORE_APOYO.get(self.apoyo_familiar, 0)
        s += 1 if self.cuidador_es_unico else 0
        s += self._SCORE_EMOCIONAL.get(self.estado_emocional_cuidador, 0)
        s += 1 if self.cuidador_perdio_trabajo else 0
        s += 1 if self.abandono_escolar else 0
        s += self._SCORE_IMPACTO.get(self.impacto_emocional_paciente, 0)
        return s

    @staticmethod
    def nivel_desde_puntaje(score):
        if score >= 17:
            return EvaluacionPsicosocial.NivelRiesgo.CRITICO
        if score >= 11:
            return EvaluacionPsicosocial.NivelRiesgo.ALTO
        if score >= 5:
            return EvaluacionPsicosocial.NivelRiesgo.MEDIO
        return EvaluacionPsicosocial.NivelRiesgo.BAJO

    def save(self, *args, **kwargs):
        self.puntaje_total = self.calcular_puntaje()
        self.nivel_riesgo = self.nivel_desde_puntaje(self.puntaje_total)
        super().save(*args, **kwargs)
