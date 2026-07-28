from django.contrib import admin
from .models import CasoClinico, NotaCaso


class NotaCasoInline(admin.TabularInline):
    model = NotaCaso
    extra = 0
    fields = ('tipo', 'titulo', 'autor', 'es_importante', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(CasoClinico)
class CasoClinicoAdmin(admin.ModelAdmin):
    list_display = ('codigo_caso', 'paciente', 'tipo_cancer', 'estado', 'prioridad',
                    'medico_responsable', 'fecha_apertura')
    list_filter  = ('estado', 'prioridad', 'tipo_cancer')
    search_fields = ('codigo_caso', 'paciente__nombres', 'paciente__apellidos', 'titulo')
    readonly_fields = ('codigo_caso', 'created_at', 'updated_at')
    inlines = [NotaCasoInline]
    date_hierarchy = 'fecha_apertura'


@admin.register(NotaCaso)
class NotaCasoAdmin(admin.ModelAdmin):
    list_display  = ('caso', 'tipo', 'titulo', 'autor', 'es_importante', 'created_at')
    list_filter   = ('tipo', 'es_importante')
    search_fields = ('titulo', 'contenido', 'caso__codigo_caso')
    readonly_fields = ('created_at', 'updated_at')
