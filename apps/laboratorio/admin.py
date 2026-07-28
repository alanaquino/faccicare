from django.contrib import admin

from .models import CatalogoEstudio, CatalogoParametro, ResultadoLaboratorio, ValorResultado


class CatalogoParametroInline(admin.TabularInline):
    model = CatalogoParametro
    extra = 0
    fields = (
        'nombre', 'tipo_valor', 'unidad', 'referencia_minima', 'referencia_maxima',
        'referencia_texto', 'requiere_comentario', 'alerta_critica', 'activo', 'orden',
    )


class ValorResultadoInline(admin.TabularInline):
    model = ValorResultado
    extra = 0
    fields = (
        'parametro_catalogo', 'parametro', 'valor', 'unidad', 'referencia_min',
        'referencia_max', 'referencia_texto', 'comentario', 'bandera', 'orden',
    )
    readonly_fields = ('bandera',)


@admin.register(CatalogoEstudio)
class CatalogoEstudioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'activo', 'updated_at')
    list_filter = ('categoria', 'activo')
    search_fields = ('nombre', 'categoria', 'descripcion')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CatalogoParametroInline]


@admin.register(CatalogoParametro)
class CatalogoParametroAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'estudio', 'tipo_valor', 'unidad', 'referencia_minima',
        'referencia_maxima', 'requiere_comentario', 'alerta_critica', 'activo',
    )
    list_filter = (
        'estudio', 'tipo_valor', 'requiere_comentario', 'alerta_critica', 'activo',
    )
    search_fields = ('nombre', 'estudio__nombre', 'referencia_texto', 'alerta_sistema')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ResultadoLaboratorio)
class ResultadoLaboratorioAdmin(admin.ModelAdmin):
    list_display = ('nombre_examen', 'paciente', 'tipo', 'fecha_muestra', 'estado', 'hay_valores_criticos')
    list_filter = ('tipo', 'estado', 'hay_valores_criticos', 'fecha_muestra')
    search_fields = ('nombre_examen', 'paciente__nombres', 'paciente__apellidos')
    readonly_fields = ('created_at', 'updated_at', 'hay_valores_criticos')
    inlines = [ValorResultadoInline]
    date_hierarchy = 'fecha_muestra'


@admin.register(ValorResultado)
class ValorResultadoAdmin(admin.ModelAdmin):
    list_display = ('parametro', 'parametro_catalogo', 'valor', 'unidad', 'bandera', 'resultado')
    list_filter = ('bandera', 'parametro_catalogo__estudio')
    search_fields = (
        'parametro', 'parametro_catalogo__nombre', 'parametro_catalogo__estudio__nombre',
        'resultado__nombre_examen',
    )
    readonly_fields = ('bandera', 'valor_numerico')
