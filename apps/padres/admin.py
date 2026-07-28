from django.contrib import admin
from .models import PadreTutor, RecursoEducativo, RegistroTomaMedicamento, ReporteSintoma


@admin.register(PadreTutor)
class PadreTutorAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'parentesco', 'nacionalidad', 'provincia', 'municipio', 'created_at')
    list_filter = ('parentesco', 'nacionalidad', 'provincia')
    search_fields = ('usuario__first_name', 'usuario__last_name', 'usuario__email', 'nacionalidad')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(ReporteSintoma)
class ReporteSintomaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'gravedad', 'fecha_inicio', 'sintomas_str', 'created_at')
    list_filter = ('gravedad', 'fecha_inicio')
    search_fields = ('paciente__nombres', 'paciente__apellidos')
    readonly_fields = ('id', 'created_at')


@admin.register(RecursoEducativo)
class RecursoEducativoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'categoria', 'orden', 'activo', 'created_at')
    list_filter = ('categoria', 'activo')
    search_fields = ('titulo', 'descripcion_corta', 'contenido')
    readonly_fields = ('id', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('titulo',)}
    ordering = ('orden', 'titulo')


@admin.register(RegistroTomaMedicamento)
class RegistroTomaMedicamentoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'nombre_medicamento', 'indice', 'fecha', 'tomado_a', 'tutor')
    list_filter = ('fecha',)
    search_fields = ('paciente__nombres', 'paciente__apellidos', 'nombre_medicamento')
    readonly_fields = ('id', 'tomado_a')
    date_hierarchy = 'fecha'
