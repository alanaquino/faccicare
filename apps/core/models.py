import sys

from django.conf import settings
from django.db import models


class CentroSalud(models.Model):

    class Tipo(models.TextChoices):
        HOSPITAL    = 'hospital',          'Nivel 3 (Especializado)'
        CLINICA     = 'clinica',           'Nivel 2 (General)'
        UNIDAD      = 'unidad_atencion',   'Unidad de Atención Primaria'
        DIAGNOSTICO = 'centro_diagnostico','Centro Diagnóstico'
        OTRO        = 'otro',              'Otro'

    class EstadoDerivacion(models.TextChoices):
        DISPONIBLE     = 'disponible',     'Disponible para derivación'
        LIMITADO       = 'limitado',       'Capacidad limitada'
        NO_DISPONIBLE  = 'no_disponible',  'No disponible'
        MANTENIMIENTO  = 'mantenimiento',  'En mantenimiento'

    # ── Información general ──────────────────────────────────────────
    nombre    = models.CharField(max_length=150, verbose_name='Nombre del centro')
    tipo      = models.CharField(max_length=30, choices=Tipo.choices, default=Tipo.HOSPITAL)
    provincia = models.CharField(max_length=100, blank=True, verbose_name='Provincia / Ciudad')
    municipio = models.CharField(max_length=100, blank=True)
    direccion = models.CharField(max_length=255, blank=True, verbose_name='Dirección exacta')
    telefono  = models.CharField(max_length=30, blank=True)
    correo    = models.EmailField(blank=True)

    # ── Capacidades clínicas ─────────────────────────────────────────
    camas_disponibles  = models.PositiveIntegerField(default=0, verbose_name='Camas oncológicas disponibles')
    camas_total        = models.PositiveIntegerField(default=0, verbose_name='Camas oncológicas total')
    estado_derivacion  = models.CharField(
        max_length=20,
        choices=EstadoDerivacion.choices,
        default=EstadoDerivacion.DISPONIBLE,
        verbose_name='Estado de derivación',
    )

    # ── Especialidades (checkboxes) ──────────────────────────────────
    esp_oncologia_pediatrica  = models.BooleanField(default=False, verbose_name='Oncología Pediátrica')
    esp_pediatria_general     = models.BooleanField(default=False, verbose_name='Pediatría General')
    esp_imagenes_diagnosticas = models.BooleanField(default=False, verbose_name='Imágenes Diagnósticas')
    esp_laboratorio_avanzado  = models.BooleanField(default=False, verbose_name='Laboratorio Clínico Avanzado')

    # ── Personal y entrenamiento ─────────────────────────────────────
    medicos_titulares = models.PositiveIntegerField(default=0, verbose_name='Médicos titulares en turno')
    entrenados_facci  = models.PositiveIntegerField(default=0, verbose_name='Entrenados FACCI')

    # ── Ubicación ────────────────────────────────────────────────────
    latitud  = models.FloatField(null=True, blank=True, verbose_name='Latitud')
    longitud = models.FloatField(null=True, blank=True, verbose_name='Longitud')
    direccion_normalizada = models.CharField(max_length=255, blank=True, null=True)
    coordenadas_actualizadas = models.DateTimeField(blank=True, null=True)

    activo        = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ['nombre']
        verbose_name = 'Centro de salud'
        verbose_name_plural = 'Centros de salud'

    def __str__(self):
        return self.nombre

    def _geocodificacion_habilitada(self):
        if getattr(self, '_skip_geocoding', False):
            return False
        if getattr(settings, 'FACCI_GEOCODING_ENABLED', None) is not None:
            return bool(settings.FACCI_GEOCODING_ENABLED)
        return 'test' not in sys.argv

    def _debe_geocodificar(self):
        if not self._geocodificacion_habilitada():
            return False

        from apps.core.geocoding import normalizar_direccion_centro

        direccion_actual = normalizar_direccion_centro(self)
        if not direccion_actual:
            return False
        if self.latitud is None or self.longitud is None:
            return True
        return self.direccion_normalizada != direccion_actual

    def save(self, *args, **kwargs):
        if self._debe_geocodificar():
            from apps.core.geocoding import aplicar_geocodificacion_centro

            aplicar_geocodificacion_centro(self)
            update_fields = kwargs.get('update_fields')
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {
                    'latitud',
                    'longitud',
                    'direccion_normalizada',
                    'coordenadas_actualizadas',
                }
        super().save(*args, **kwargs)


class LogActividad(models.Model):
    class TipoAccion(models.TextChoices):
        CREACION = 'CREACION', 'Creacion'
        EDICION = 'EDICION', 'Edicion'
        ELIMINACION = 'ELIMINACION', 'Eliminacion'
        CONSULTA = 'CONSULTA', 'Consulta'
        LOGIN = 'LOGIN', 'Inicio de sesion'
        LOGOUT = 'LOGOUT', 'Cierre de sesion'
        REPORTE = 'REPORTE', 'Generacion de reporte'

    usuario     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    accion      = models.CharField(max_length=80)
    tipo_accion = models.CharField(
        max_length=20,
        choices=TipoAccion.choices,
        default=TipoAccion.CONSULTA,
        db_index=True,
    )
    modelo      = models.CharField(max_length=100)
    modulo      = models.CharField(max_length=80, blank=True, db_index=True)
    objeto_id   = models.CharField(max_length=80, blank=True)
    objeto_repr = models.CharField(max_length=220, blank=True)
    descripcion = models.TextField(blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    fecha       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Log de actividad"
        verbose_name_plural = "Logs de actividad"
        indexes = [
            models.Index(fields=['fecha'], name='logactividad_fecha_idx'),
            models.Index(fields=['tipo_accion'], name='logactividad_tipo_idx'),
            models.Index(fields=['modulo'], name='logactividad_modulo_idx'),
        ]

    def __str__(self):
        return f'{self.fecha:%Y-%m-%d %H:%M} - {self.accion}'

    def save(self, *args, **kwargs):
        if not self.tipo_accion:
            self.tipo_accion = self._inferir_tipo_accion()
        if not self.modulo:
            self.modulo = self._inferir_modulo()
        super().save(*args, **kwargs)

    def _inferir_tipo_accion(self):
        accion = (self.accion or '').lower()
        if any(palabra in accion for palabra in ['crear', 'creacion', 'registrar', 'nuevo', 'subir', 'cargar', 'agendar', 'solicitar']):
            return self.TipoAccion.CREACION
        if any(palabra in accion for palabra in ['editar', 'actualizar', 'cambio', 'revisar', 'resolver', 'descartar']):
            return self.TipoAccion.EDICION
        if any(palabra in accion for palabra in ['eliminar', 'borrar']):
            return self.TipoAccion.ELIMINACION
        if any(palabra in accion for palabra in ['login', 'inicio de sesion', 'iniciar sesion']):
            return self.TipoAccion.LOGIN
        if any(palabra in accion for palabra in ['logout', 'cierre de sesion', 'cerrar sesion']):
            return self.TipoAccion.LOGOUT
        if any(palabra in accion for palabra in ['reporte', 'exportar']):
            return self.TipoAccion.REPORTE
        return self.TipoAccion.CONSULTA

    def _inferir_modulo(self):
        modelo = (self.modelo or '').lower()
        mapa = {
            'paciente': 'Pacientes',
            'cuestionariocribado': 'Cribado',
            'referenciamedica': 'Referencias',
            'seguimientopaciente': 'Seguimiento',
            'alertaclinica': 'Alertas',
            'documentomedico': 'Documentos',
            'solicituddocumento': 'Documentos',
            'reportegenerado': 'Reportes',
            'customuser': 'Usuarios',
        }
        return mapa.get(modelo, self.modelo or 'Sistema')

    @property
    def tipo_color(self):
        return {
            self.TipoAccion.CREACION: 'tertiary',
            self.TipoAccion.EDICION: 'primary',
            self.TipoAccion.ELIMINACION: 'error',
            self.TipoAccion.CONSULTA: 'outline',
            self.TipoAccion.LOGIN: 'secondary',
            self.TipoAccion.LOGOUT: 'secondary',
            self.TipoAccion.REPORTE: 'orange',
        }.get(self.tipo_accion, 'outline')

    @property
    def tipo_icono(self):
        return {
            self.TipoAccion.CREACION: 'add_circle',
            self.TipoAccion.EDICION: 'edit',
            self.TipoAccion.ELIMINACION: 'delete',
            self.TipoAccion.CONSULTA: 'visibility',
            self.TipoAccion.LOGIN: 'login',
            self.TipoAccion.LOGOUT: 'logout',
            self.TipoAccion.REPORTE: 'bar_chart',
        }.get(self.tipo_accion, 'history')


class SistemaConfiguracion(models.Model):
    # Campos antiguos/compatibilidad
    logo = models.ImageField(upload_to='logo/', null=True, blank=True, verbose_name='Logo del sistema (Legacy)')
    nombre_institucion = models.CharField(
        max_length=150,
        default='Fundación de Apoyo Contra el Cáncer Infantil (FACCI)',
        verbose_name='Nombre de la institución'
    )
    
    # Nuevos campos para diferenciar logos y nombres
    nombre_aplicacion = models.CharField(
        max_length=150,
        default='FACCI Care',
        verbose_name='Nombre de la aplicación'
    )
    logo_aplicacion = models.ImageField(
        upload_to='logo_app/',
        null=True,
        blank=True,
        verbose_name='Logo de la aplicación'
    )
    logo_reportes = models.ImageField(
        upload_to='logo_reportes/',
        null=True,
        blank=True,
        verbose_name='Logo oficial para reportes'
    )

    class Meta:
        verbose_name = 'Configuración del sistema'
        verbose_name_plural = 'Configuraciones del sistema'

    def __str__(self):
        return "Configuración del Sistema"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj

    @property
    def logo_url(self):
        # Mantenemos logo_url para compatibilidad retrógrada
        return self.logo_aplicacion_url

    @property
    def logo_aplicacion_url(self):
        if self.logo_aplicacion:
            return self.logo_aplicacion.url
        elif self.logo:
            return self.logo.url
        from django.templatetags.static import static
        return static('img/Logo-Facci-1.png')

    @property
    def logo_reportes_url(self):
        if self.logo_reportes:
            return self.logo_reportes.url
        elif self.logo:
            return self.logo.url
        from django.templatetags.static import static
        return static('img/Logo-Facci-1.png')


