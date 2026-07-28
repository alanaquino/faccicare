from django.db import migrations, models


def mostrar_documentos_subidos_por_tutores(apps, schema_editor):
    DocumentoMedico = apps.get_model('documentos', 'DocumentoMedico')
    DocumentoMedico.objects.filter(
        subido_por__rol='PADRE_TUTOR',
    ).update(visible_padre=True)


class Migration(migrations.Migration):

    dependencies = [
        ('documentos', '0002_documentomedico_estado_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentomedico',
            name='visible_padre',
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text='Permite consultar este documento desde el Portal Padres.',
                verbose_name='Visible para padre/tutor',
            ),
        ),
        migrations.RunPython(
            mostrar_documentos_subidos_por_tutores,
            migrations.RunPython.noop,
        ),
    ]
