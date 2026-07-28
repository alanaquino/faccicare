"""
Migración de datos: siembra el catálogo de estudios de laboratorio y sus
parámetros, necesario para el formulario "Valores del examen" (el desplegable
"Estudio" / "Parámetro" salía vacío sin estos datos).

IMPORTANTE: Los rangos de referencia son VALORES REFERENCIALES estándar de
adulto/pediátrico general. El equipo de laboratorio/médico debe revisarlos y
ajustarlos según edad y protocolo (especialmente en pediatría). Se pueden editar
desde el panel de administración (CatalogoParametro).
"""
from decimal import Decimal
from django.db import migrations


def _d(value):
    return Decimal(value) if value is not None else None


ESTUDIOS = [
    {
        'nombre': 'Hemograma completo (BHC)',
        'categoria': 'Hematología',
        'descripcion': 'Biometría hemática completa.',
        'parametros': [
            {'nombre': 'Hemoglobina', 'unidad': 'g/dL', 'min': '11.5', 'max': '15.5', 'critica': True},
            {'nombre': 'Hematocrito', 'unidad': '%', 'min': '35', 'max': '45'},
            {'nombre': 'Leucocitos', 'unidad': '10³/µL', 'min': '4.5', 'max': '13.5'},
            {'nombre': 'Neutrófilos absolutos', 'unidad': '/µL', 'min': '1500', 'max': '8000', 'critica': True},
            {'nombre': 'Linfocitos', 'unidad': '%', 'min': '20', 'max': '50'},
            {'nombre': 'Plaquetas', 'unidad': '10³/µL', 'min': '150', 'max': '450', 'critica': True},
        ],
    },
    {
        'nombre': 'Química sanguínea',
        'categoria': 'Química clínica',
        'descripcion': 'Panel metabólico básico.',
        'parametros': [
            {'nombre': 'Glucosa', 'unidad': 'mg/dL', 'min': '70', 'max': '110'},
            {'nombre': 'Urea', 'unidad': 'mg/dL', 'min': '15', 'max': '40'},
            {'nombre': 'Creatinina', 'unidad': 'mg/dL', 'min': '0.3', 'max': '0.7'},
            {'nombre': 'Ácido úrico', 'unidad': 'mg/dL', 'min': '2.5', 'max': '6.0'},
        ],
    },
    {
        'nombre': 'Perfil hepático',
        'categoria': 'Química clínica',
        'descripcion': 'Pruebas de función hepática.',
        'parametros': [
            {'nombre': 'AST (TGO)', 'unidad': 'U/L', 'min': '10', 'max': '40'},
            {'nombre': 'ALT (TGP)', 'unidad': 'U/L', 'min': '7', 'max': '40'},
            {'nombre': 'Fosfatasa alcalina', 'unidad': 'U/L', 'min': '100', 'max': '320'},
            {'nombre': 'Bilirrubina total', 'unidad': 'mg/dL', 'min': '0.2', 'max': '1.2'},
        ],
    },
    {
        'nombre': 'Electrolitos séricos',
        'categoria': 'Química clínica',
        'descripcion': 'Sodio, potasio, cloro y calcio.',
        'parametros': [
            {'nombre': 'Sodio', 'unidad': 'mEq/L', 'min': '135', 'max': '145'},
            {'nombre': 'Potasio', 'unidad': 'mEq/L', 'min': '3.5', 'max': '5.1', 'critica': True},
            {'nombre': 'Cloro', 'unidad': 'mEq/L', 'min': '98', 'max': '107'},
            {'nombre': 'Calcio', 'unidad': 'mg/dL', 'min': '8.5', 'max': '10.5'},
        ],
    },
    {
        'nombre': 'Examen general de orina (EGO)',
        'categoria': 'Uroanálisis',
        'descripcion': 'Análisis físico, químico y microscópico de orina.',
        'parametros': [
            {'nombre': 'Densidad', 'unidad': '', 'min': '1.005', 'max': '1.030'},
            {'nombre': 'pH', 'unidad': '', 'min': '5.0', 'max': '8.0'},
            {'nombre': 'Proteínas', 'unidad': '', 'texto': 'Negativo', 'tipo': 'resultado'},
            {'nombre': 'Glucosa en orina', 'unidad': '', 'texto': 'Negativo', 'tipo': 'resultado'},
        ],
    },
]


def crear_catalogo(apps, schema_editor):
    CatalogoEstudio = apps.get_model('laboratorio', 'CatalogoEstudio')
    CatalogoParametro = apps.get_model('laboratorio', 'CatalogoParametro')

    for estudio_data in ESTUDIOS:
        estudio, _ = CatalogoEstudio.objects.get_or_create(
            nombre=estudio_data['nombre'],
            defaults={
                'categoria': estudio_data['categoria'],
                'descripcion': estudio_data.get('descripcion', ''),
                'activo': True,
            },
        )
        for orden, p in enumerate(estudio_data['parametros'], start=1):
            CatalogoParametro.objects.get_or_create(
                estudio=estudio,
                nombre=p['nombre'],
                defaults={
                    'unidad': p.get('unidad', ''),
                    'referencia_minima': _d(p.get('min')),
                    'referencia_maxima': _d(p.get('max')),
                    'referencia_texto': p.get('texto', ''),
                    'tipo_valor': p.get('tipo', 'numerico'),
                    'alerta_critica': p.get('critica', False),
                    'orden': orden,
                    'activo': True,
                },
            )


def eliminar_catalogo(apps, schema_editor):
    CatalogoEstudio = apps.get_model('laboratorio', 'CatalogoEstudio')
    # Borra los estudios sembrados (los parámetros caen por CASCADE).
    CatalogoEstudio.objects.filter(
        nombre__in=[e['nombre'] for e in ESTUDIOS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0002_catalogoestudio_valorresultado_comentario_and_more'),
    ]

    operations = [
        migrations.RunPython(crear_catalogo, eliminar_catalogo),
    ]
