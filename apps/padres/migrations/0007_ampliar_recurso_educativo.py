from django.db import migrations, models
from django.utils.text import slugify


def poblar_slugs(apps, schema_editor):
    RecursoEducativo = apps.get_model('padres', 'RecursoEducativo')
    usados = set()

    for recurso in RecursoEducativo.objects.order_by('created_at'):
        base = slugify(recurso.titulo) or 'recurso'
        slug = base
        suffix = 2
        while slug in usados or RecursoEducativo.objects.filter(slug=slug).exclude(pk=recurso.pk).exists():
            slug = f'{base}-{suffix}'
            suffix += 1
        recurso.slug = slug
        recurso.save(update_fields=['slug'])
        usados.add(slug)


class Migration(migrations.Migration):

    dependencies = [
        ('padres', '0006_padretutor_nacionalidad'),
    ]

    operations = [
        migrations.AddField(
            model_name='recursoeducativo',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='recursoeducativo',
            name='descripcion_corta',
            field=models.TextField(blank=True, help_text='Resumen que se muestra en la tarjeta del recurso', verbose_name='Descripción corta'),
        ),
        migrations.AddField(
            model_name='recursoeducativo',
            name='contenido',
            field=models.TextField(blank=True, verbose_name='Contenido completo'),
        ),
        migrations.AddField(
            model_name='recursoeducativo',
            name='actividades',
            field=models.JSONField(blank=True, default=list, verbose_name='Actividades recomendadas'),
        ),
        migrations.AddField(
            model_name='recursoeducativo',
            name='pasos_padres',
            field=models.JSONField(blank=True, default=list, verbose_name='Qué puede hacer el padre, madre o tutor'),
        ),
        migrations.AddField(
            model_name='recursoeducativo',
            name='cuando_contactar',
            field=models.JSONField(blank=True, default=list, verbose_name='Cuándo contactar al equipo médico'),
        ),
        migrations.AddField(
            model_name='recursoeducativo',
            name='imagen',
            field=models.CharField(blank=True, help_text='Ruta dentro de static (ej. img/recurso.jpg) o URL absoluta', max_length=500, verbose_name='Imagen'),
        ),
        migrations.AddField(
            model_name='recursoeducativo',
            name='video_url',
            field=models.URLField(blank=True, help_text='Enlace opcional de YouTube', verbose_name='Video relacionado'),
        ),
        migrations.AddField(
            model_name='recursoeducativo',
            name='orden',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Orden'),
        ),
        migrations.AlterField(
            model_name='recursoeducativo',
            name='categoria',
            field=models.CharField(choices=[('ALIMENTACION', 'Alimentación'), ('APOYO_EMOCIONAL', 'Apoyo Emocional'), ('PREGUNTAS_FRECUENTES', 'Preguntas Frecuentes'), ('MEDICAMENTOS', 'Medicamentos'), ('ACTIVIDAD_FISICA', 'Actividad Física'), ('HIGIENE', 'Higiene'), ('JUEGOS_ACTIVIDADES', 'Juegos y Actividades'), ('APOYO_ESCOLAR', 'Apoyo Escolar'), ('SENALES_ALERTA', 'Señales de Alerta'), ('CUIDADO_CASA', 'Cuidado en Casa'), ('OTRO', 'Otro')], default='OTRO', max_length=50, verbose_name='Categoría'),
        ),
        migrations.RunPython(poblar_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='recursoeducativo',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, unique=True, verbose_name='Identificador URL'),
        ),
        migrations.AlterModelOptions(
            name='recursoeducativo',
            options={'ordering': ['orden', 'titulo'], 'verbose_name': 'Recurso Educativo', 'verbose_name_plural': 'Recursos Educativos'},
        ),
    ]
