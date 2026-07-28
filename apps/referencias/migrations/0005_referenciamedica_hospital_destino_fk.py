from django.db import migrations, models
import django.db.models.deletion

from apps.core.centros_matching import match_centro_por_nombre


def poblar(apps, schema_editor):
    Referencia = apps.get_model('referencias', 'ReferenciaMedica')
    CentroSalud = apps.get_model('core', 'CentroSalud')
    for ref in Referencia.objects.all():
        centro = match_centro_por_nombre(CentroSalud, ref.hospital_destino)
        if centro is not None:
            ref.hospital_destino_fk_id = centro.id
            ref.save(update_fields=['hospital_destino_fk'])


def revertir(apps, schema_editor):
    Referencia = apps.get_model('referencias', 'ReferenciaMedica')
    for ref in Referencia.objects.all():
        ref.hospital_destino = ref.hospital_destino_fk.nombre if ref.hospital_destino_fk_id else ''
        ref.save(update_fields=['hospital_destino'])


class Migration(migrations.Migration):

    dependencies = [
        ('referencias', '0004_contrarreferencia_estudios_realizados'),
        ('core', '0007_sistemaconfiguracion_logo_aplicacion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='referenciamedica',
            name='hospital_destino_fk',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='referencias_destino',
                to='core.centrosalud',
                verbose_name='Hospital / Centro de destino',
            ),
        ),
        migrations.RunPython(poblar, revertir),
        migrations.RemoveField(model_name='referenciamedica', name='hospital_destino'),
        migrations.RenameField(
            model_name='referenciamedica',
            old_name='hospital_destino_fk',
            new_name='hospital_destino',
        ),
    ]
