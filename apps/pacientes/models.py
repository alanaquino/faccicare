import os
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.padres.models import PadreTutor
from apps.core.encryption import EncryptedTextField


class Paciente(models.Model):

    class Sexo(models.TextChoices):
        MASCULINO = 'M', 'Masculino'
        FEMENINO  = 'F', 'Femenino'

    class TipoSangre(models.TextChoices):
        A_POS  = 'A+',  'A+'
        A_NEG  = 'A-',  'A-'
        B_POS  = 'B+',  'B+'
        B_NEG  = 'B-',  'B-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        O_POS  = 'O+',  'O+'
        O_NEG  = 'O-',  'O-'

    class EstadoPaciente(models.TextChoices):
        SOSPECHOSO     = 'SOSPECHOSO',     'Sospechoso'
        REFERIDO       = 'REFERIDO',       'Referido'
        EN_ESTUDIO     = 'EN_ESTUDIO',     'En estudio'
        CONFIRMADO     = 'CONFIRMADO',     'Confirmado'
        DESCARTADO     = 'DESCARTADO',     'Descartado'
        EN_TRATAMIENTO = 'EN_TRATAMIENTO', 'En tratamiento'
        EN_REMISION    = 'EN_REMISION',    'En remisión'
        FINALIZADO     = 'FINALIZADO',     'Finalizado'

    class Diagnostico(models.TextChoices):
        LEUCEMIA       = 'LEUCEMIA',       'Leucemia'
        TUMORES_SNC    = 'TUMORES_SNC',    'Tumores del SNC'
        RETINOBLASTOMA = 'RETINOBLASTOMA', 'Retinoblastoma'
        TUMOR_WILMS    = 'TUMOR_WILMS',    'Tumor de Wilms'
        NEUROBLASTOMA  = 'NEUROBLASTOMA',  'Neuroblastoma'
        OTRO           = 'OTRO',           'Otro'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    codigo_paciente = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código de paciente',
        help_text='Código único generado automáticamente (ej. FACCI-20240001)',
        db_index=True,
    )
    nombres = models.CharField(
        max_length=150,
        verbose_name='Nombres',
    )
    apellidos = models.CharField(
        max_length=150,
        verbose_name='Apellidos',
    )
    fecha_nacimiento = models.DateField(
        verbose_name='Fecha de nacimiento',
    )
    sexo = models.CharField(
        max_length=1,
        choices=Sexo.choices,
        verbose_name='Sexo',
    )
    tipo_sangre = models.CharField(
        max_length=3,
        choices=TipoSangre.choices,
        blank=True,
        verbose_name='Tipo de sangre',
    )
    peso = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Peso (kg)',
    )
    altura = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Altura (cm)',
    )
    direccion = EncryptedTextField(
        blank=True,
        verbose_name='Dirección',
    )
    provincia = models.CharField(
        max_length=100,
        verbose_name='Provincia',
    )
    municipio = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Municipio',
    )
    escuela = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Escuela',
    )
    seguro_medico = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Seguro médico',
    )
    numero_seguro = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Número de seguro',
    )
    alergias = EncryptedTextField(
        blank=True,
        verbose_name='Alergias conocidas',
        help_text='Listar alergias separadas por coma',
    )
    antecedentes_medicos = EncryptedTextField(
        blank=True,
        verbose_name='Antecedentes médicos',
        help_text='Historial de enfermedades, cirugías y condiciones previas',
    )
    estado_actual = models.CharField(
        max_length=20,
        choices=EstadoPaciente.choices,
        default=EstadoPaciente.SOSPECHOSO,
        verbose_name='Estado actual',
        db_index=True,
    )
    diagnostico = models.CharField(
        max_length=20,
        choices=Diagnostico.choices,
        blank=True,
        default='',
        db_index=True,
        verbose_name='Diagnóstico',
    )
    fotografia = models.ImageField(
        upload_to='pacientes/',
        blank=True,
        verbose_name='Fotografía',
    )
    padre_tutor = models.ForeignKey(
        PadreTutor,
        on_delete=models.PROTECT,
        related_name='pacientes',
        verbose_name='Padre / Tutor',
    )
    medico_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pacientes_asignados',
        verbose_name='Médico asignado',
        limit_choices_to={'rol__in': ['MEDICO', 'PEDIATRA', 'ONCOLOGO', 'PERSONAL_FACCI']},
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pacientes_creados',
        verbose_name='Creado por',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Registrado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Paciente'
        verbose_name_plural = 'Pacientes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['codigo_paciente'], name='paciente_codigo_idx'),
            models.Index(fields=['estado_actual'], name='paciente_estado_idx'),
            models.Index(fields=['padre_tutor'], name='paciente_padre_idx'),
            models.Index(fields=['provincia'], name='paciente_provincia_idx'),
        ]

    def __str__(self):
        return f'{self.nombre_completo} — {self.codigo_paciente}'

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'

    @property
    def nombre(self):
        return self.nombres

    @property
    def apellido(self):
        return self.apellidos

    @property
    def iniciales(self):
        if self.nombres and self.apellidos:
            return f"{self.nombres[0]}{self.apellidos[0]}".upper()
        return self.nombres[:2].upper() if self.nombres else "PA"

    @property
    def edad(self):
        hoy = timezone.now().date()
        birth = self.fecha_nacimiento
        if not birth:
            return "N/D"
        years = hoy.year - birth.year - ((hoy.month, hoy.day) < (birth.month, birth.day))
        months = hoy.month - birth.month
        if hoy.day < birth.day:
            months -= 1
        months = months % 12
        if years > 0:
            if months > 0:
                return f"{years} años, {months} meses"
            return f"{years} años"
        return f"{months} meses"

    @property
    def fecha(self):
        # Formato legible: e.g. "12 Oct, 2023"
        meses = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
        d = self.created_at
        if not d:
            return "Reciente"
        return f"{d.day} {meses.get(d.month, '')}, {d.year}"

    @property
    def estado(self):
        return self.get_estado_actual_display()

    @property
    def estado_color(self):
        if self.estado_actual in ['EN_TRATAMIENTO', 'REFERIDO', 'SOSPECHOSO']:
            return 'error'
        elif self.estado_actual in ['FINALIZADO', 'DESCARTADO']:
            return 'tertiary'
        return 'secondary'

    @property
    def medico(self):
        return self.medico_asignado.nombre_completo if self.medico_asignado else 'No asignado'

    @property
    def prioridad(self):
        if self.estado_actual in ['EN_TRATAMIENTO', 'REFERIDO']:
            return 'Alta'
        elif self.estado_actual in ['FINALIZADO', 'DESCARTADO']:
            return 'Baja'
        return 'Media'


class NotaClinica(models.Model):

    class TipoNota(models.TextChoices):
        EVOLUCION = 'EVOLUCION', 'Evolucion'
        DIAGNOSTICO = 'DIAGNOSTICO', 'Diagnostico'
        TRATAMIENTO = 'TRATAMIENTO', 'Tratamiento'
        OBSERVACION = 'OBSERVACION', 'Observacion'
        ALERTA = 'ALERTA', 'Alerta clinica'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='notas_clinicas',
        verbose_name='Paciente',
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='notas_clinicas_creadas',
        verbose_name='Autor',
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoNota.choices,
        default=TipoNota.EVOLUCION,
        verbose_name='Tipo de nota',
        db_index=True,
    )
    texto = models.TextField(
        verbose_name='Nota clinica',
    )
    adjunto = models.FileField(
        upload_to='notas_clinicas/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Adjunto',
        help_text='Archivo opcional asociado a la nota clinica',
    )
    es_importante = models.BooleanField(
        default=False,
        verbose_name='Marcar como importante',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Registrada el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizada el')

    class Meta:
        verbose_name = 'Nota clinica'
        verbose_name_plural = 'Notas clinicas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['paciente'], name='nota_paciente_idx'),
            models.Index(fields=['tipo'], name='nota_tipo_idx'),
            models.Index(fields=['created_at'], name='nota_fecha_idx'),
        ]

    def __str__(self):
        return f'{self.paciente.nombre_completo} - {self.get_tipo_display()}'

    @property
    def nombre_adjunto(self):
        return os.path.basename(self.adjunto.name) if self.adjunto else ''

    @property
    def extension_adjunto(self):
        _, ext = os.path.splitext(self.nombre_adjunto)
        return ext.lower().lstrip('.')

    @property
    def tamano_adjunto(self):
        if not self.adjunto:
            return ''
        try:
            size = self.adjunto.size
            if size < 1024:
                return f'{size} B'
            if size < 1024 * 1024:
                return f'{size / 1024:.1f} KB'
            return f'{size / (1024 * 1024):.1f} MB'
        except OSError:
            return ''

    @property
    def autor_nombre(self):
        return self.autor.nombre_completo if self.autor else 'Sistema'

    @property
    def fecha(self):
        meses = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
        d = self.created_at
        if not d:
            return 'Reciente'
        return f'{d.day} {meses.get(d.month, "")}, {d.year}'

    @property
    def color(self):
        if self.tipo == self.TipoNota.ALERTA or self.es_importante:
            return 'error'
        if self.tipo == self.TipoNota.TRATAMIENTO:
            return 'secondary'
        if self.tipo == self.TipoNota.DIAGNOSTICO:
            return 'primary'
        return 'tertiary'
