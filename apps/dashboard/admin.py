from django.contrib import admin

from .models import AlertaClinica


@admin.register(AlertaClinica)
class AlertaClinicaAdmin(admin.ModelAdmin):
    list_display = (
        'titulo',
        'paciente',
        'tipo_alerta',
        'prioridad',
        'estado',
        'fecha_creacion',
        'fecha_limite',
        'revisado_por',
    )
    list_filter = ('tipo_alerta', 'prioridad', 'estado', 'fecha_creacion')
    search_fields = (
        'titulo',
        'descripcion',
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__codigo_paciente',
    )
    readonly_fields = ('id', 'clave_dedupe', 'fecha_creacion', 'updated_at')
    raw_id_fields = (
        'paciente',
        'cribado',
        'referencia',
        'seguimiento',
        'documento',
        'solicitud_documento',
        'revisado_por',
    )
