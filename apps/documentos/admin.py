from django.contrib import admin
from django.utils.html import format_html
from .models import DocumentoMedico, SolicitudDocumento


@admin.register(DocumentoMedico)
class DocumentoMedicoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'tipo_display', 'estado_badge', 'visible_padre', 'fecha_documento', 'subido_por', 'tamanio_display', 'created_at')
    list_filter = ('tipo_documento', 'estado', 'visible_padre', 'fecha_documento', 'created_at')
    search_fields = ('paciente__nombres', 'paciente__apellidos', 'descripcion')
    readonly_fields = ('id', 'created_at', 'updated_at', 'nombre_archivo', 'tamano', 'extension')
    ordering = ('-fecha_documento',)

    fieldsets = (
        ('Informacion General', {
            'fields': ('id', 'paciente', 'subido_por')
        }),
        ('Documento', {
            'fields': ('tipo_documento', 'archivo', 'nombre_archivo', 'extension', 'tamano')
        }),
        ('Detalles', {
            'fields': ('descripcion', 'fecha_documento', 'estado', 'visible_padre')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def tipo_display(self, obj):
        return obj.get_tipo_documento_display()
    tipo_display.short_description = 'Tipo'

    def estado_badge(self, obj):
        colors = {
            'PENDIENTE': '#FFC107',
            'REVISADO': '#28A745',
            'CORRECCION': '#DC3545',
        }
        color = colors.get(obj.estado, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def tamanio_display(self, obj):
        return obj.tamano
    tamanio_display.short_description = 'Tamaño'


@admin.register(SolicitudDocumento)
class SolicitudDocumentoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'titulo', 'estado_badge', 'medico_solicitante', 'tiene_documento', 'created_at')
    list_filter = ('estado', 'created_at', 'medico_solicitante')
    search_fields = ('paciente__nombres', 'paciente__apellidos', 'titulo', 'descripcion')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Solicitud', {
            'fields': ('id', 'paciente', 'medico_solicitante', 'titulo', 'descripcion')
        }),
        ('Documento', {
            'fields': ('documento_asociado', 'estado')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def estado_badge(self, obj):
        colors = {
            'PENDIENTE': '#FFC107',
            'SUBIDO': '#17A2B8',
            'REVISADO': '#28A745',
            'CORRECCION': '#DC3545',
        }
        color = colors.get(obj.estado, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'

    def tiene_documento(self, obj):
        if obj.documento_asociado:
            return format_html('<span style="color: green;">✓ Si</span>')
        return format_html('<span style="color: red;">✗ No</span>')
    tiene_documento.short_description = 'Documento Asociado'
