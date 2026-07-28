import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.core.encryption import EncryptedCharField


class CustomUser(AbstractUser):

    class Rol(models.TextChoices):
        ADMIN              = 'ADMIN',              'Administrador'
        MEDICO             = 'MEDICO',             'Médico General'
        PEDIATRA           = 'PEDIATRA',           'Pediatra'
        ONCOLOGO           = 'ONCOLOGO',           'Oncólogo'
        PERSONAL_FACCI     = 'PERSONAL_FACCI',     'Coordinador FACCI'
        TRABAJADORA_SOCIAL = 'TRABAJADORA_SOCIAL', 'Trabajo Social / Psicología'
        ENFERMERA          = 'ENFERMERA',          'Enfermera / Técnico de Salud'
        PADRE_TUTOR        = 'PADRE_TUTOR',        'Padre / Tutor'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    telefono = EncryptedCharField(
        blank=True,
        verbose_name='Teléfono',
        help_text='Número de contacto principal',
    )
    class TipoDocumento(models.TextChoices):
        CEDULA = 'CEDULA', 'Cédula'
        PASAPORTE = 'PASAPORTE', 'Pasaporte'

    tipo_documento = models.CharField(
        max_length=20,
        choices=TipoDocumento.choices,
        default=TipoDocumento.CEDULA,
        verbose_name='Tipo de documento',
    )
    cedula = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        default=None,
        verbose_name='Cédula',
        help_text='Cédula de identidad dominicana (ej. 001-0000000-0)',
    )
    foto_perfil = models.ImageField(
        upload_to='perfiles/',
        blank=True,
        verbose_name='Foto de perfil',
    )
    rol = models.CharField(
        max_length=25,
        choices=Rol.choices,
        default=Rol.MEDICO,
        verbose_name='Rol',
        db_index=True,
    )
    especialidad = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Especialidad médica',
    )
    centro_medico = models.ForeignKey(
        'core.CentroSalud',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
        verbose_name='Centro médico',
        help_text='Hospital o clínica donde labora',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado el')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado el')

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email'], name='customuser_email_idx'),
            models.Index(fields=['cedula'], name='customuser_cedula_idx'),
            models.Index(fields=['rol'], name='customuser_rol_idx'),
        ]

    def __str__(self):
        return f'{self.get_full_name()} ({self.get_rol_display()})'

    @property
    def nombre_completo(self):
        return self.get_full_name() or self.username

    @property
    def nombre(self):
        return self.nombre_completo

    @property
    def es_personal_medico(self):
        """Todos los roles del portal médico (excluye PADRE_TUTOR)."""
        return self.rol in (
            self.Rol.MEDICO,
            self.Rol.PEDIATRA,
            self.Rol.ONCOLOGO,
            self.Rol.PERSONAL_FACCI,
            self.Rol.TRABAJADORA_SOCIAL,
            self.Rol.ENFERMERA,
        )

    @property
    def es_medico_clinico(self):
        """Roles con autoridad clínica directa: MEDICO, PEDIATRA, ONCOLOGO."""
        return self.rol in (self.Rol.MEDICO, self.Rol.PEDIATRA, self.Rol.ONCOLOGO)

    @property
    def es_trabajadora_social(self):
        """Trabajo Social / Psicología — gestiona psicosocial y Casa FACCI."""
        return self.rol == self.Rol.TRABAJADORA_SOCIAL

    @property
    def es_enfermera(self):
        """Enfermera / Técnico de Salud — registra signos vitales y muestras."""
        return self.rol == self.Rol.ENFERMERA

    @property
    def es_staff_facci(self):
        """Equipo no clínico de FACCI: Coordinador + Trabajo Social."""
        return self.rol in (self.Rol.PERSONAL_FACCI, self.Rol.TRABAJADORA_SOCIAL)

    # ──────────────────────────────────────────────────────────────────
    # MATRIZ DE ACCESO POR MÓDULO (Módulo × Rol)
    #
    # `puede_ver_*`       → tiene algún acceso: controla la visibilidad en el
    #                       menú (sidebar) y la lectura de la página.
    # `puede_gestionar_*` / `puede_crear_*` / `puede_generar_*`
    #                     → acciones de escritura (crear / editar / generar).
    #
    # Es la ÚNICA fuente de verdad: el sidebar y los decoradores de las vistas
    # deben usar estas propiedades para mantenerse sincronizados con la matriz.
    # ──────────────────────────────────────────────────────────────────

    @property
    def es_personal(self):
        """Cualquier usuario del portal médico (todo el personal menos Padre/Tutor)."""
        return self.rol != self.Rol.PADRE_TUTOR

    @property
    def _equipo_asistencial(self):
        """Clínicos (MED/PED/ONC) + Enfermería + Admin. Excluye Trabajo Social y FACCI."""
        return self.es_medico_clinico or self.rol in (self.Rol.ENFERMERA, self.Rol.ADMIN)

    @property
    def _equipo_clinico_ampliado(self):
        """Equipo asistencial + Trabajo Social. Excluye al Coordinador FACCI."""
        return self._equipo_asistencial or self.rol == self.Rol.TRABAJADORA_SOCIAL

    @property
    def es_equipo_facci(self):
        """Equipo FACCI: Coordinador FACCI + Trabajo Social + Admin."""
        return self.es_staff_facci or self.rol == self.Rol.ADMIN

    # ── Lectura / visibilidad en menú ──────────────────────────────────
    @property
    def puede_ver_pacientes(self):
        """Pacientes: todo el personal (clínicos gestionan, T.Social/FACCI solo lectura)."""
        return self.es_personal

    @property
    def puede_ver_alertas(self):
        """Alertas clínicas: todo el personal menos el Coordinador FACCI."""
        return self._equipo_clinico_ampliado

    @property
    def puede_ver_cribado(self):
        """Cribado: clínicos + enfermería + admin (ONC en solo lectura)."""
        return self._equipo_asistencial

    @property
    def puede_ver_referencias(self):
        """Referencias: equipo clínico ampliado y Coordinación FACCI en lectura."""
        return self._equipo_clinico_ampliado or self.rol == self.Rol.PERSONAL_FACCI

    @property
    def puede_ver_seguimiento(self):
        """Seguimiento clínico: equipo clínico ampliado (T.Social solo lectura)."""
        return self._equipo_clinico_ampliado

    @property
    def puede_ver_indicaciones(self):
        """Indicaciones médicas: clínicos + enfermería + admin (ENF solo lectura)."""
        return self._equipo_asistencial

    @property
    def puede_ver_laboratorio(self):
        """Laboratorio: clínicos + enfermería + admin (sin T.Social ni FACCI)."""
        return self._equipo_asistencial

    @property
    def puede_ver_psicosocial(self):
        """Psicosocial: solo equipo FACCI (Coordinador, Trabajo Social) + Admin."""
        return self.es_equipo_facci

    @property
    def puede_ver_alojamiento(self):
        """Casa FACCI: equipo FACCI + clínicos (MED/PED/ONC) en lectura. Sin enfermería."""
        return self.es_equipo_facci or self.es_medico_clinico

    @property
    def puede_ver_reportes(self):
        """Reportes / PENCI-RD: todo el personal en solo lectura. Solo ADMIN genera."""
        return self.es_personal

    @property
    def puede_ver_matrices(self):
        """Matrices operativas: solo Admin y Coordinador FACCI (no figura en la matriz)."""
        return self.rol in (self.Rol.ADMIN, self.Rol.PERSONAL_FACCI)

    # ── Escritura / acciones ───────────────────────────────────────────
    @property
    def puede_hacer_cribado(self):
        """Crear cribados: detección (MEDICO, PEDIATRA)."""
        return self.rol in (self.Rol.MEDICO, self.Rol.PEDIATRA)

    @property
    def puede_gestionar_referencias(self):
        """Crear/editar referencias: clínicos + admin (ENF y T.Social solo lectura)."""
        return self.es_medico_clinico or self.rol == self.Rol.ADMIN

    @property
    def puede_gestionar_indicaciones(self):
        """Crear/editar indicaciones: clínicos + admin (ENF solo lectura)."""
        return self.es_medico_clinico or self.rol == self.Rol.ADMIN

    @property
    def puede_gestionar_psicosocial(self):
        """Crear/editar evaluaciones psicosociales: Trabajo Social + admin."""
        return self.rol in (self.Rol.TRABAJADORA_SOCIAL, self.Rol.ADMIN)

    @property
    def puede_gestionar_alojamiento(self):
        """Gestionar Casa FACCI: Trabajo Social + Coordinador FACCI + admin."""
        return self.rol in (self.Rol.TRABAJADORA_SOCIAL, self.Rol.PERSONAL_FACCI, self.Rol.ADMIN)

    @property
    def puede_subir_documentos(self):
        """Subir/gestionar documentos: todo el personal menos FACCI (solo lectura)."""
        return self._equipo_clinico_ampliado

    @property
    def puede_generar_reportes(self):
        """Generar/exportar/enviar reportes: Admin y Coordinador FACCI (resto solo lectura)."""
        return self.rol in (self.Rol.ADMIN, self.Rol.PERSONAL_FACCI)

    @property
    def rol_color(self):
        if self.rol == self.Rol.ADMIN:
            return 'error'
        elif self.rol in [self.Rol.MEDICO, self.Rol.PEDIATRA, self.Rol.ENFERMERA]:
            return 'primary'
        elif self.rol == self.Rol.ONCOLOGO:
            return 'secondary'
        elif self.rol in [self.Rol.PERSONAL_FACCI, self.Rol.TRABAJADORA_SOCIAL]:
            return 'tertiary'
        return 'outline'

    @property
    def estado(self):
        return 'Activo' if self.is_active else 'Inactivo'

    @property
    def estado_color(self):
        return 'tertiary' if self.is_active else 'error'

    @property
    def ultimo_acceso(self):
        d = self.last_login
        if not d:
            return "Hace poco"
        return d.strftime("%d %b, %H:%M")

    @property
    def iniciales(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        return self.username[:2].upper()

    @property
    def provincia(self):
        # Derivada del centro de salud donde labora
        if self.centro_medico and self.centro_medico.provincia:
            return self.centro_medico.provincia
        if self.centro_medico and 'santiago' in self.centro_medico.nombre.lower():
            return "Santiago"
        return "Santo Domingo"
