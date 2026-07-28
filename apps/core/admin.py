from django.contrib import admin

from .geocoding import guardar_geocodificacion_centro
from .models import CentroSalud, LogActividad

@admin.register(CentroSalud)
class CentroSaludAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'provincia', 'municipio', 'latitud', 'longitud', 'activo')
    list_filter = ('tipo', 'provincia', 'activo')
    search_fields = ('nombre', 'provincia', 'municipio', 'direccion')
    readonly_fields = ('direccion_normalizada', 'coordenadas_actualizadas')
    actions = ('actualizar_coordenadas_automaticamente',)

    @admin.action(description='Actualizar coordenadas automaticamente')
    def actualizar_coordenadas_automaticamente(self, request, queryset):
        actualizados = 0
        sin_resultado = 0
        for centro in queryset:
            if guardar_geocodificacion_centro(centro):
                actualizados += 1
            else:
                sin_resultado += 1
        self.message_user(
            request,
            f'Coordenadas actualizadas: {actualizados}. Sin resultado: {sin_resultado}.',
        )

@admin.register(LogActividad)
class LogActividadAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'usuario', 'tipo_accion', 'modulo', 'accion', 'modelo', 'objeto_id', 'direccion_ip')
    list_filter = ('tipo_accion', 'modulo', 'accion', 'modelo', 'fecha')
    search_fields = ('descripcion', 'accion', 'modelo', 'modulo', 'objeto_repr', 'usuario__username')
    readonly_fields = ('fecha',)

admin.site.site_header = 'FACCI Care - Administracion'
admin.site.site_title = 'FACCI Care'
admin.site.index_title = 'Panel de gestion clinica'
