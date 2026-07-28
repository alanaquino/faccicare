from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Q

from .models import CuestionarioCribado


def marcar_como_referido(modeladmin, request, queryset):
    actualizados = queryset.update(requiere_referencia=True)
    modeladmin.message_user(request, f'{actualizados} cribados marcados para referencia.')


marcar_como_referido.short_description = 'Marcar como requiere referencia'


def generar_alerta(modeladmin, request, queryset):
    cribados_alto = queryset.filter(nivel_riesgo=CuestionarioCribado.NivelRiesgo.ALTO)
    count = cribados_alto.count()
    modeladmin.message_user(request, f'{count} cribados con riesgo alto detectados.')


generar_alerta.short_description = 'Generar alerta de riesgo alto'


@admin.register(CuestionarioCribado)
class CuestionarioCribadoAdmin(admin.ModelAdmin):
    list_display = (
        'paciente_link',
        'medico',
        'fecha_evaluacion_formateada',
        'puntaje_total',
        'nivel_riesgo_badge',
        'requiere_referencia',
    )
    list_filter = (
        'nivel_riesgo',
        'resultado',
        'requiere_referencia',
        'fecha_evaluacion',
    )
    search_fields = (
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__codigo_paciente',
        'medico__username',
        'medico__first_name',
        'medico__last_name',
    )
    readonly_fields = (
        'id',
        'fecha_evaluacion',
        'created_at',
        'updated_at',
        'puntaje_total',
        'tiene_alarma_mayor',
        'resultado_calculado',
    )
    date_hierarchy = 'fecha_evaluacion'
    actions = [marcar_como_referido, generar_alerta]

    fieldsets = (
        ('Información General', {
            'fields': ('id', 'paciente', 'medico', 'fecha_evaluacion'),
        }),
        ('Síntomas Generales', {
            'fields': (
                'fiebre_persistente',
                'perdida_peso',
                'dolor_huesos',
                'palidez',
                'fatiga',
            ),
        }),
        ('Signos Hematológicos', {
            'fields': (
                'moretones',
                'sangrado',
                'ganglios',
                'infecciones_recurrentes',
            ),
        }),
        ('Signos Neurológicos y Masas', {
            'fields': (
                'dolor_cabeza',
                'vomitos',
                'masa_abdominal',
            ),
        }),
        ('Resultado y Evaluación', {
            'fields': (
                'puntaje_total',
                'tiene_alarma_mayor',
                'nivel_riesgo',
                'resultado',
                'resultado_calculado',
                'requiere_referencia',
            ),
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def paciente_link(self, obj):
        url = reverse('admin:pacientes_paciente_change', args=[obj.paciente.id])
        return format_html(
            '<a href="{}">{} ({})</a>',
            url,
            obj.paciente.nombre_completo,
            obj.paciente.codigo_paciente,
        )
    paciente_link.short_description = 'Paciente'

    def fecha_evaluacion_formateada(self, obj):
        return obj.fecha_evaluacion.strftime('%d/%m/%Y %H:%M') if obj.fecha_evaluacion else '—'
    fecha_evaluacion_formateada.short_description = 'Fecha Evaluación'

    def nivel_riesgo_badge(self, obj):
        colores = {
            'ALTO': '#ba1a1a',
            'MEDIO': '#6d4ea2',
            'BAJO': '#006a62',
        }
        color = colores.get(obj.nivel_riesgo, '#999999')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_nivel_riesgo_display(),
        )
    nivel_riesgo_badge.short_description = 'Nivel de Riesgo'

    def resultado_calculado(self, obj):
        return format_html(
            '{} (Puntaje: {}/{})',
            obj.get_resultado_display(),
            obj.puntaje_total,
            len(CuestionarioCribado.CAMPOS_SINTOMAS),
        )
    resultado_calculado.short_description = 'Resultado Calculado'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('paciente', 'medico')

