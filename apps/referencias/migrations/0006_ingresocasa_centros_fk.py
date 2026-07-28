from django.db import migrations, models
import django.db.models.deletion

from apps.core.centros_matching import match_centro_por_nombre


def poblar(apps, schema_editor):
    Ingreso = apps.get_model('referencias', 'ReferenciaIngresoCasaFACCI')
    CentroSalud = apps.get_model('core', 'CentroSalud')
    casa_facci, _ = CentroSalud.objects.get_or_create(
        nombre='Casa FACCI',
        defaults={'tipo': 'otro', 'provincia': 'Santiago', 'municipio': 'Santiago'},
    )
    for ing in Ingreso.objects.all():
        origen = match_centro_por_nombre(CentroSalud, ing.centro_origen)
        if origen is not None:
            ing.centro_origen_fk_id = origen.id
        destino = match_centro_por_nombre(CentroSalud, ing.hospital_destino)
        ing.hospital_destino_fk_id = (destino or casa_facci).id
        ing.save(update_fields=['centro_origen_fk', 'hospital_destino_fk'])


def revertir(apps, schema_editor):
    Ingreso = apps.get_model('referencias', 'ReferenciaIngresoCasaFACCI')
    for ing in Ingreso.objects.all():
        ing.centro_origen = ing.centro_origen_fk.nombre if ing.centro_origen_fk_id else ''
        ing.hospital_destino = ing.hospital_destino_fk.nombre if ing.hospital_destino_fk_id else 'Casa FACCI'
        ing.save(update_fields=['centro_origen', 'hospital_destino'])


class Migration(migrations.Migration):

    dependencies = [
        ('referencias', '0005_referenciamedica_hospital_destino_fk'),
        ('core', '0007_sistemaconfiguracion_logo_aplicacion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='referenciaingresocasafacci',
            name='centro_origen_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ingresos_origen',
                to='core.centrosalud',
                verbose_name='Centro de origen',
            ),
        ),
        migrations.AddField(
            model_name='referenciaingresocasafacci',
            name='hospital_destino_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ingresos_destino',
                to='core.centrosalud',
                verbose_name='Hospital / destino',
            ),
        ),
        migrations.RunPython(poblar, revertir),
        migrations.RemoveField(model_name='referenciaingresocasafacci', name='centro_origen'),
        migrations.RemoveField(model_name='referenciaingresocasafacci', name='hospital_destino'),
        migrations.RenameField(
            model_name='referenciaingresocasafacci',
            old_name='centro_origen_fk', new_name='centro_origen',
        ),
        migrations.RenameField(
            model_name='referenciaingresocasafacci',
            old_name='hospital_destino_fk', new_name='hospital_destino',
        ),
    ]
