from django.contrib import admin
from .models import Notificacion


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'tipo', 'prioridad', 'modulo', 'titulo', 'leida', 'archivada', 'created_at')
    list_filter = ('tipo', 'prioridad', 'modulo', 'leida', 'archivada', 'created_at')
    search_fields = ('titulo', 'mensaje', 'usuario__username', 'usuario__email', 'objeto_id', 'clave_dedupe')
    readonly_fields = ('id', 'created_at', 'updated_at', 'fecha_lectura')
