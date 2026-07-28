from django.contrib import admin
from .models import Contrarreferencia, ReferenciaIngresoCasaFACCI, ReferenciaMedica


@admin.register(ReferenciaMedica)
class ReferenciaMedicaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'paciente', 'hospital_destino', 'prioridad', 'estado', 'fecha_referencia')
    list_filter = ('prioridad', 'estado', 'fecha_referencia')
    search_fields = ('paciente__nombres', 'paciente__apellidos', 'hospital_destino__nombre', 'motivo_referencia')
    readonly_fields = ('id', 'created_at', 'updated_at', 'fecha_referencia')
    ordering = ('-fecha_referencia',)


@admin.register(Contrarreferencia)
class ContrarreferenciaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'referencia', 'resultado_atencion', 'tipo_cancer', 'estadio', 'fecha_atencion', 'requiere_seguimiento_facci')
    list_filter = ('resultado_atencion', 'tipo_cancer', 'estadio', 'requiere_seguimiento_facci')
    search_fields = ('referencia__paciente__nombres', 'referencia__paciente__apellidos', 'diagnostico')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(ReferenciaIngresoCasaFACCI)
class ReferenciaIngresoCasaFACCIAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'paciente', 'fecha_entrada', 'fecha_salida', 'habitacion', 'estado', 'creado_por')
    list_filter = ('estado', 'fecha_entrada', 'habitacion')
    search_fields = (
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__codigo_paciente',
        'responsable_paciente',
        'centro_origen__nombre',
        'hospital_destino__nombre',
    )
    readonly_fields = ('id', 'fecha_creacion', 'fecha_actualizacion')
    ordering = ('-fecha_creacion',)
