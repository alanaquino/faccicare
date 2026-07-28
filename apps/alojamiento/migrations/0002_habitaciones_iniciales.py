"""
Migración de datos: crea las habitaciones iniciales de Casa FACCI.
Estas habitaciones son necesarias para el módulo de alojamiento (CU-34/35/36).
"""
import uuid
from django.db import migrations


HABITACIONES = [
    {'nombre': 'Habitación 1 — Planta Baja', 'capacidad': 3, 'descripcion': 'Planta baja, acceso sin escaleras, baño compartido.'},
    {'nombre': 'Habitación 2 — Planta Baja', 'capacidad': 2, 'descripcion': 'Planta baja, baño privado.'},
    {'nombre': 'Habitación 3 — Planta Alta', 'capacidad': 4, 'descripcion': 'Planta alta, vista al jardín, baño compartido.'},
    {'nombre': 'Habitación 4 — Planta Alta', 'capacidad': 2, 'descripcion': 'Planta alta, uso preferencial para madres lactantes.'},
    {'nombre': 'Habitación 5 — Ala Norte',   'capacidad': 3, 'descripcion': 'Ala norte, baño privado, aire acondicionado.'},
]


def crear_habitaciones(apps, schema_editor):
    HabitacionCasa = apps.get_model('alojamiento', 'HabitacionCasa')
    for h in HABITACIONES:
        if not HabitacionCasa.objects.filter(nombre=h['nombre']).exists():
            HabitacionCasa.objects.create(
                id=uuid.uuid4(),
                nombre=h['nombre'],
                capacidad=h['capacidad'],
                descripcion=h['descripcion'],
                activa=True,
            )


def eliminar_habitaciones(apps, schema_editor):
    HabitacionCasa = apps.get_model('alojamiento', 'HabitacionCasa')
    for h in HABITACIONES:
        HabitacionCasa.objects.filter(nombre=h['nombre']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('alojamiento', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(crear_habitaciones, eliminar_habitaciones),
    ]
