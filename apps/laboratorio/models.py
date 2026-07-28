import uuid
from decimal import Decimal, InvalidOperation

from django.db import models
from django.utils import timezone


class CatalogoEstudio(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=180, unique=True)
    categoria = models.CharField(max_length=120, blank=True, db_index=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['categoria', 'nombre']
        verbose_name = 'Catálogo de estudio'
        verbose_name_plural = 'Catálogo de estudios'

    def __str__(self):
        return self.nombre


class CatalogoParametro(models.Model):
    class TipoValor(models.TextChoices):
        NUMERICO = 'numerico', 'Numérico'
        TEXTO = 'texto', 'Texto'
        RESULTADO = 'resultado', 'Resultado'
        POSITIVO_NEGATIVO = 'positivo_negativo', 'Positivo/Negativo'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estudio = models.ForeignKey(
        CatalogoEstudio, on_delete=models.CASCADE, related_name='parametros'
    )
    nombre = models.CharField(max_length=180)
    unidad = models.CharField(max_length=60, blank=True)
    referencia_minima = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    referencia_maxima = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    referencia_texto = models.CharField(max_length=180, blank=True)
    requiere_comentario = models.BooleanField(default=False)
    comentario_sugerido = models.TextField(blank=True)
    alerta_sistema = models.TextField(blank=True)
    alerta_critica = models.BooleanField(default=False, db_index=True)
    tipo_valor = models.CharField(
        max_length=20, choices=TipoValor.choices, default=TipoValor.NUMERICO, db_index=True
    )
    activo = models.BooleanField(default=True, db_index=True)
    orden = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['estudio__nombre', 'orden', 'nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['estudio', 'nombre'], name='lab_catalogo_parametro_unico'
            )
        ]
        indexes = [
            models.Index(fields=['estudio', 'activo'], name='lab_cat_param_est_act_idx'),
            models.Index(fields=['tipo_valor'], name='lab_cat_param_tipo_idx'),
        ]
        verbose_name = 'Catálogo de parámetro'
        verbose_name_plural = 'Catálogo de parámetros'

    def __str__(self):
        return f'{self.estudio.nombre} - {self.nombre}'


class ResultadoLaboratorio(models.Model):
    class TipoExamen(models.TextChoices):
        HEMOGRAMA = 'HEMOGRAMA', 'Hemograma / BHC'
        QUIMICA = 'QUIMICA', 'Química sanguínea'
        COAGULACION = 'COAGULACION', 'Coagulación'
        ORINA = 'ORINA', 'Análisis de orina'
        CULTIVO = 'CULTIVO', 'Cultivo microbiológico'
        IMAGENOLOGIA = 'IMAGENOLOGIA', 'Imagenología'
        PATOLOGIA = 'PATOLOGIA', 'Anatomía Patológica'
        MARCADORES = 'MARCADORES', 'Marcadores tumorales'
        OTRO = 'OTRO', 'Otro'

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        RECIBIDO = 'RECIBIDO', 'Recibido'
        REVISADO = 'REVISADO', 'Revisado'
        CRITICO = 'CRITICO', 'Valores críticos'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        'pacientes.Paciente', on_delete=models.CASCADE, related_name='resultados_laboratorio'
    )
    solicitado_por = models.ForeignKey(
        'auth_app.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resultados_lab_solicitados',
    )
    revisado_por = models.ForeignKey(
        'auth_app.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='resultados_lab_revisados',
    )
    tipo = models.CharField(max_length=20, choices=TipoExamen.choices, db_index=True)
    nombre_examen = models.CharField(max_length=200)
    fecha_muestra = models.DateField(db_index=True)
    fecha_resultado = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.RECIBIDO, db_index=True,
    )
    resultado_narrativo = models.TextField(blank=True)
    archivo = models.FileField(upload_to='laboratorio/%Y/%m/', null=True, blank=True)
    observaciones = models.TextField(blank=True)
    hay_valores_criticos = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_muestra', '-created_at']
        indexes = [
            models.Index(fields=['paciente', 'fecha_muestra'], name='lab_pcte_fecha_idx'),
            models.Index(fields=['paciente', 'tipo'], name='lab_pcte_tipo_idx'),
        ]
        verbose_name = 'Resultado de laboratorio'
        verbose_name_plural = 'Resultados de laboratorio'

    def __str__(self):
        return f"{self.nombre_examen} — {self.paciente} ({self.fecha_muestra})"

    @property
    def codigo(self):
        year = self.created_at.year if self.created_at else timezone.now().year
        seq = str(self.pk)[-4:].upper()
        return f"LAB-{year}-{seq}"

    def actualizar_criticos(self):
        critico = self.valores.filter(
            bandera__in=[ValorResultado.Bandera.CRITICO_BAJO, ValorResultado.Bandera.CRITICO_ALTO]
        ).exists()
        fields = []
        if critico != self.hay_valores_criticos:
            self.hay_valores_criticos = critico
            fields.append('hay_valores_criticos')
        nuevo_estado = (
            self.Estado.CRITICO if critico
            else (self.Estado.RECIBIDO if self.estado == self.Estado.CRITICO else self.estado)
        )
        if nuevo_estado != self.estado:
            self.estado = nuevo_estado
            fields.append('estado')
        if fields:
            fields.append('updated_at')
            self.save(update_fields=fields)
        return critico


class ValorResultado(models.Model):
    class Bandera(models.TextChoices):
        NORMAL = 'NORMAL', 'Normal'
        BAJO = 'BAJO', 'Bajo'
        ALTO = 'ALTO', 'Alto'
        CRITICO_BAJO = 'CRITICO_BAJO', 'Crítico bajo'
        CRITICO_ALTO = 'CRITICO_ALTO', 'Crítico alto'
        SIN_RANGO = 'SIN_RANGO', 'Sin rango'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resultado = models.ForeignKey(
        ResultadoLaboratorio, on_delete=models.CASCADE, related_name='valores',
    )
    parametro_catalogo = models.ForeignKey(
        CatalogoParametro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resultados',
    )
    parametro = models.CharField(max_length=120)
    valor = models.CharField(max_length=100)
    valor_numerico = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    unidad = models.CharField(max_length=50, blank=True)
    referencia_min = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    referencia_max = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    referencia_texto = models.CharField(max_length=180, blank=True)
    comentario = models.TextField(blank=True)
    bandera = models.CharField(
        max_length=15, choices=Bandera.choices, default=Bandera.SIN_RANGO, db_index=True,
    )
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'parametro']
        verbose_name = 'Valor de resultado'
        verbose_name_plural = 'Valores de resultado'

    def __str__(self):
        return f"{self.parametro}: {self.valor} {self.unidad}"

    def _requiere_bandera_critica(self, bandera):
        if not self.parametro_catalogo or not self.parametro_catalogo.alerta_critica:
            return False
        return bandera in [self.Bandera.BAJO, self.Bandera.ALTO]

    def _calcular_bandera_cualitativa(self):
        if not self.parametro_catalogo or not self.parametro_catalogo.alerta_critica:
            return self.Bandera.SIN_RANGO

        texto = (self.valor or '').strip().lower()
        if not texto:
            return self.Bandera.SIN_RANGO

        normalizadores = [
            'negativo', 'no detectable', 'indetectable', 'normal', 'libre',
            'conservado', 'estable', 'sin mutacion', 'sin mutación',
        ]
        if any(patron in texto for patron in normalizadores):
            return self.Bandera.NORMAL

        alertadores = [
            'positivo', 'detectado', 'presente', 'maligno', 'comprometido',
            'alterado', 'mutacion', 'mutación', 'amplificacion', 'amplificación',
            'rearrangement', 'fusion', 'fusión',
        ]
        if any(patron in texto for patron in alertadores):
            return self.Bandera.CRITICO_ALTO

        return self.Bandera.SIN_RANGO

    def _calcular_bandera(self):
        if self.valor_numerico is None:
            return self._calcular_bandera_cualitativa()
        if self.referencia_min is None and self.referencia_max is None:
            return self.Bandera.SIN_RANGO
        v = float(self.valor_numerico)
        if self.referencia_min is not None:
            ref = float(self.referencia_min)
            if v < ref:
                bandera = self.Bandera.CRITICO_BAJO if ref > 0 and v < ref * 0.7 else self.Bandera.BAJO
                return self.Bandera.CRITICO_BAJO if self._requiere_bandera_critica(bandera) else bandera
        if self.referencia_max is not None:
            ref = float(self.referencia_max)
            if v > ref:
                bandera = self.Bandera.CRITICO_ALTO if ref > 0 and v > ref * 1.3 else self.Bandera.ALTO
                return self.Bandera.CRITICO_ALTO if self._requiere_bandera_critica(bandera) else bandera
        return self.Bandera.NORMAL

    def save(self, *args, **kwargs):
        try:
            self.valor_numerico = Decimal(str(self.valor).replace(',', '.'))
        except (InvalidOperation, ValueError, ArithmeticError):
            self.valor_numerico = None
        self.bandera = self._calcular_bandera()
        super().save(*args, **kwargs)
