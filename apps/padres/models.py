import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from apps.core.encryption import EncryptedCharField, EncryptedTextField


class PadreTutor(models.Model):

    class EstadoCivil(models.TextChoices):
        SOLTERO   = 'SOLTERO',   'Soltero/a'
        CASADO    = 'CASADO',    'Casado/a'
        UNION_LIBRE = 'UNION_LIBRE', 'Unión libre'
        DIVORCIADO = 'DIVORCIADO', 'Divorciado/a'
        VIUDO     = 'VIUDO',     'Viudo/a'

    class Parentesco(models.TextChoices):
        PADRE  = 'PADRE',  'Padre'
        MADRE  = 'MADRE',  'Madre'
        ABUELO = 'ABUELO', 'Abuelo/a'
        TIO    = 'TIO',    'Tío/a'
        TUTOR  = 'TUTOR',  'Tutor legal'
        OTRO   = 'OTRO',   'Otro'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_padre',
        verbose_name='Usuario',
    )
    parentesco = models.CharField(
        max_length=20,
        choices=Parentesco.choices,
        default=Parentesco.PADRE,
        verbose_name='Parentesco',
    )
    nacionalidad = models.CharField(
        max_length=80,
        blank=True,
        null=True,
        default='Dominicana',
        verbose_name='Nacionalidad',
        help_text='Nacionalidad legal del padre, madre o tutor responsable',
    )
    direccion = EncryptedTextField(
        verbose_name='Dirección',
        help_text='Dirección completa de residencia',
    )
    provincia = models.CharField(
        max_length=100,
        verbose_name='Provincia',
    )
    municipio = models.CharField(
        max_length=100,
        verbose_name='Municipio',
    )
    ocupacion = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Ocupación',
    )
    contacto_emergencia = EncryptedCharField(
        blank=True,
        verbose_name='Contacto de emergencia',
        help_text='Nombre del contacto de emergencia',
    )
    telefono_emergencia = EncryptedCharField(
        blank=True,
        verbose_name='Teléfono de emergencia',
    )
    estado_civil = models.CharField(
        max_length=20,
        choices=EstadoCivil.choices,
        blank=True,
        verbose_name='Estado civil',
    )
    cantidad_hijos = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='Cantidad de hijos',
    )
    ingresos_aproximados = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Ingresos aproximados',
        help_text='Rango mensual en pesos dominicanos (ej. RD$10,000–20,000)',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Padre / Tutor'
        verbose_name_plural = 'Padres / Tutores'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['provincia'], name='padretutor_provincia_idx'),
        ]

    def __str__(self):
        return f'{self.usuario.get_full_name()} ({self.get_parentesco_display()})'


class ReporteSintoma(models.Model):

    class Gravedad(models.TextChoices):
        LEVE     = 'Leve',     'Leve'
        MODERADA = 'Moderada', 'Moderada'
        SEVERA   = 'Severa',   'Severa'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        'pacientes.Paciente',
        on_delete=models.CASCADE,
        related_name='reportes_sintomas',
        verbose_name='Paciente',
    )
    tutor = models.ForeignKey(
        PadreTutor,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reportes_sintomas',
        verbose_name='Tutor reportante',
    )
    fecha_inicio = models.DateField(verbose_name='Fecha de inicio')
    gravedad = models.CharField(
        max_length=20,
        choices=Gravedad.choices,
        default=Gravedad.LEVE,
        verbose_name='Gravedad',
    )
    sintomas = models.JSONField(default=list, verbose_name='Síntomas reportados')
    descripcion = models.TextField(blank=True, verbose_name='Descripción adicional')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Enviado el')

    class Meta:
        verbose_name = 'Reporte de Síntomas'
        verbose_name_plural = 'Reportes de Síntomas'
        ordering = ['-created_at']

    def __str__(self):
        return f'Síntomas de {self.paciente} — {self.created_at.strftime("%d/%m/%Y")}'

    @property
    def sintomas_str(self):
        return ', '.join(self.sintomas) if self.sintomas else 'Sin especificar'

    @property
    def color_gravedad(self):
        return {'Leve': 'tertiary', 'Moderada': 'secondary', 'Severa': 'error'}.get(self.gravedad, 'primary')


class RecursoEducativo(models.Model):

    class Categoria(models.TextChoices):
        ALIMENTACION = 'ALIMENTACION', 'Alimentación'
        APOYO_EMOCIONAL = 'APOYO_EMOCIONAL', 'Apoyo Emocional'
        PREGUNTAS_FRECUENTES = 'PREGUNTAS_FRECUENTES', 'Preguntas Frecuentes'
        MEDICAMENTOS = 'MEDICAMENTOS', 'Medicamentos'
        ACTIVIDAD_FISICA = 'ACTIVIDAD_FISICA', 'Actividad Física'
        HIGIENE = 'HIGIENE', 'Higiene'
        JUEGOS_ACTIVIDADES = 'JUEGOS_ACTIVIDADES', 'Juegos y Actividades'
        APOYO_ESCOLAR = 'APOYO_ESCOLAR', 'Apoyo Escolar'
        SENALES_ALERTA = 'SENALES_ALERTA', 'Señales de Alerta'
        CUIDADO_CASA = 'CUIDADO_CASA', 'Cuidado en Casa'
        OTRO = 'OTRO', 'Otro'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    titulo = models.CharField(
        max_length=255,
        verbose_name='Título del recurso',
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        verbose_name='Identificador URL',
    )
    descripcion = models.TextField(
        verbose_name='Descripción',
        help_text='Contenido educativo del recurso',
    )
    descripcion_corta = models.TextField(
        blank=True,
        verbose_name='Descripción corta',
        help_text='Resumen que se muestra en la tarjeta del recurso',
    )
    contenido = models.TextField(
        blank=True,
        verbose_name='Contenido completo',
    )
    actividades = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Actividades recomendadas',
    )
    pasos_padres = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Qué puede hacer el padre, madre o tutor',
    )
    cuando_contactar = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Cuándo contactar al equipo médico',
    )
    icono = models.CharField(
        max_length=50,
        default='info',
        verbose_name='Icono Material Design',
        help_text='Nombre del icono (ej. restaurant, favorite, help)',
    )
    categoria = models.CharField(
        max_length=50,
        choices=Categoria.choices,
        default=Categoria.OTRO,
        verbose_name='Categoría',
    )
    url = models.URLField(
        blank=True,
        verbose_name='Enlace externo',
        help_text='URL opcional a recurso externo',
    )
    imagen = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Imagen',
        help_text='Ruta dentro de static (ej. img/recurso.jpg) o URL absoluta',
    )
    video_url = models.URLField(
        blank=True,
        verbose_name='Video relacionado',
        help_text='Enlace opcional de YouTube',
    )
    activo = models.BooleanField(
        default=True,
        verbose_name='Activo',
    )
    orden = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Orden',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Creado el',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Actualizado el',
    )

    class Meta:
        verbose_name = 'Recurso Educativo'
        verbose_name_plural = 'Recursos Educativos'
        ordering = ['orden', 'titulo']
        indexes = [
            models.Index(fields=['activo', 'categoria'], name='recurso_activo_cat_idx'),
        ]

    def __str__(self):
        return f'{self.titulo} ({self.get_categoria_display()})'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.titulo) or 'recurso'
            slug = base_slug
            suffix = 2
            while RecursoEducativo.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def resumen(self):
        return self.descripcion_corta or self.descripcion


class RegistroTomaMedicamento(models.Model):
    """Registra cada vez que un padre/tutor marca un medicamento como tomado."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    paciente = models.ForeignKey(
        'pacientes.Paciente',
        on_delete=models.CASCADE,
        related_name='registros_toma_medicamento',
        verbose_name='Paciente',
    )
    tutor = models.ForeignKey(
        PadreTutor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_toma_medicamento',
        verbose_name='Tutor que registró',
    )
    nombre_medicamento = models.CharField(
        max_length=200,
        verbose_name='Nombre del medicamento',
    )
    indice = models.PositiveSmallIntegerField(
        verbose_name='Índice en la lista del día',
        help_text='Posición del medicamento en la lista del día (para identificación)',
    )
    fecha = models.DateField(
        verbose_name='Fecha',
        db_index=True,
    )
    tomado_a = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Marcado como tomado a las',
    )

    class Meta:
        verbose_name = 'Registro de toma de medicamento'
        verbose_name_plural = 'Registros de toma de medicamentos'
        ordering = ['-fecha', 'indice']
        unique_together = [('paciente', 'nombre_medicamento', 'indice', 'fecha')]
        indexes = [
            models.Index(fields=['paciente', 'fecha'], name='regtoma_paciente_fecha_idx'),
        ]

    def __str__(self):
        return f'{self.nombre_medicamento} — {self.paciente} ({self.fecha})'

    @property
    def nombre_slug(self):
        return f"{self.nombre_medicamento}_{self.indice}"
