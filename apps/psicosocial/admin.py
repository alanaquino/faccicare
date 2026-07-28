from django.contrib import admin

from .models import EvaluacionPsicosocial


@admin.register(EvaluacionPsicosocial)
class EvaluacionPsicosocialAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'fecha_evaluacion', 'nivel_riesgo', 'puntaje_total', 'evaluador')
    list_filter = ('nivel_riesgo', 'requiere_seguimiento_social')
    search_fields = ('paciente__nombres', 'paciente__apellidos')
    readonly_fields = ('puntaje_total', 'nivel_riesgo', 'created_at', 'updated_at', 'codigo')
    date_hierarchy = 'fecha_evaluacion'
    fieldsets = (
        ('Identificación', {'fields': ('paciente', 'evaluador', 'fecha_evaluacion')}),
        ('Cuidador', {'fields': ('cuidador_principal_nombre', 'parentesco_cuidador', 'tipo_vivienda', 'personas_en_hogar')}),
        ('Situación económica', {'fields': ('ingreso_mensual', 'tiene_seguro_medico', 'dificultad_medicamentos', 'dificultad_transporte')}),
        ('Vivienda', {'fields': ('condicion_vivienda', 'hacinamiento', 'servicios_basicos_ausentes')}),
        ('Apoyo social', {'fields': ('apoyo_familiar', 'cuidador_es_unico')}),
        ('Bienestar del cuidador', {'fields': ('estado_emocional_cuidador', 'cuidador_perdio_trabajo', 'cuidador_requiere_apoyo_psicologico')}),
        ('Impacto en el paciente', {'fields': ('nino_en_edad_escolar', 'abandono_escolar', 'impacto_emocional_paciente')}),
        ('Resultado', {'fields': ('puntaje_total', 'nivel_riesgo')}),
        ('Plan de intervención', {'fields': ('necesidades_identificadas', 'acciones_recomendadas', 'observaciones', 'requiere_seguimiento_social', 'proxima_evaluacion')}),
    )
