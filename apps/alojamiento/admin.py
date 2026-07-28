from django.contrib import admin
from .models import EntregaHabitacion, EstanciaFamiliar, HabitacionCasa, ItemEntregaHabitacion


@admin.register(HabitacionCasa)
class HabitacionCasaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'capacidad', 'activa', 'ocupantes_actuales', 'disponible')
    list_filter = ('activa',)
    search_fields = ('nombre',)


@admin.register(EstanciaFamiliar)
class EstanciaFamiliarAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'paciente', 'habitacion', 'fecha_ingreso', 'estado', 'noches')
    list_filter = ('estado', 'motivo', 'habitacion')
    search_fields = ('paciente__nombres', 'paciente__apellidos', 'acompanante_nombre')
    date_hierarchy = 'fecha_ingreso'
    readonly_fields = ('created_at', 'updated_at')


class ItemEntregaHabitacionInline(admin.TabularInline):
    model = ItemEntregaHabitacion
    extra = 0
    fields = ('orden', 'nombre_item', 'entregado_por_facci', 'recibido_por_familiar', 'observacion')


@admin.register(EntregaHabitacion)
class EntregaHabitacionAdmin(admin.ModelAdmin):
    list_display = ('estancia', 'paciente', 'habitacion', 'fecha_entrega', 'creado_por')
    list_filter = ('fecha_entrega', 'estancia__estado', 'estancia__habitacion')
    search_fields = (
        'estancia__paciente__nombres',
        'estancia__paciente__apellidos',
        'estancia__acompanante_nombre',
        'estancia__habitacion__nombre',
    )
    readonly_fields = ('fecha_creacion', 'updated_at')
    date_hierarchy = 'fecha_entrega'
    inlines = [ItemEntregaHabitacionInline]

    @admin.display(description='Paciente')
    def paciente(self, obj):
        return obj.estancia.paciente.nombre_completo

    @admin.display(description='Habitacion')
    def habitacion(self, obj):
        return obj.estancia.habitacion.nombre


@admin.register(ItemEntregaHabitacion)
class ItemEntregaHabitacionAdmin(admin.ModelAdmin):
    list_display = ('nombre_item', 'entrega', 'entregado_por_facci', 'recibido_por_familiar')
    list_filter = ('entregado_por_facci', 'recibido_por_familiar')
    search_fields = ('nombre_item', 'entrega__estancia__paciente__nombres', 'entrega__estancia__paciente__apellidos')
