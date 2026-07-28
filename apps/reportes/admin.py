from django.contrib import admin

from .models import ReporteGenerado


@admin.register(ReporteGenerado)
class ReporteGeneradoAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'nombre_reporte', 'tipo_reporte', 'formato',
        'generado_por', 'fecha_inicio', 'fecha_fin', 'total_registros',
    )
    list_filter = ('tipo_reporte', 'formato', 'created_at')
    search_fields = (
        'nombre_reporte', 'codigo_documento', 'generado_por__username',
        'generado_por__first_name', 'generado_por__last_name',
    )
    readonly_fields = ('created_at', 'codigo_documento', 'total_registros')
