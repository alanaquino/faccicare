from django.contrib import admin

from .models import NotaClinica, Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("codigo_paciente", "nombre_completo", "estado_actual", "provincia", "created_at")
    list_filter = ("estado_actual", "provincia", "sexo")
    search_fields = ("codigo_paciente", "nombres", "apellidos")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(NotaClinica)
class NotaClinicaAdmin(admin.ModelAdmin):
    list_display = ("paciente", "tipo", "autor", "es_importante", "created_at")
    list_filter = ("tipo", "es_importante", "created_at")
    search_fields = ("paciente__codigo_paciente", "paciente__nombres", "paciente__apellidos", "texto")
    readonly_fields = ("id", "created_at", "updated_at")
