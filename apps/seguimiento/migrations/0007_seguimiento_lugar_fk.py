from django.db import migrations, models
import django.db.models.deletion

from apps.core.centros_matching import match_centro_por_nombre


def poblar(apps, schema_editor):
    Seg = apps.get_model('seguimiento', 'SeguimientoPaciente')
    CentroSalud = apps.get_model('core', 'CentroSalud')
    for s in Seg.objects.all():
        centro = match_centro_por_nombre(CentroSalud, s.lugar_seguimiento)
        if centro is not None:
            s.lugar_seguimiento_fk_id = centro.id
            s.save(update_fields=['lugar_seguimiento_fk'])


def revertir(apps, schema_editor):
    Seg = apps.get_model('seguimiento', 'SeguimientoPaciente')
    for s in Seg.objects.all():
        s.lugar_seguimiento = s.lugar_seguimiento_fk.nombre if s.lugar_seguimiento_fk_id else ''
        s.save(update_fields=['lugar_seguimiento'])


class Migration(migrations.Migration):

    dependencies = [
        ('seguimiento', '0006_remove_seguimientopaciente_lugar_cita_and_more'),
        ('core', '0007_sistemaconfiguracion_logo_aplicacion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='seguimientopaciente',
            name='lugar_seguimiento_fk',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='seguimientos',
                to='core.centrosalud',
                verbose_name='Lugar / Centro del seguimiento',
            ),
        ),
        migrations.RunPython(poblar, revertir),
        migrations.RemoveField(model_name='seguimientopaciente', name='lugar_seguimiento'),
        migrations.RenameField(
            model_name='seguimientopaciente',
            old_name='lugar_seguimiento_fk',
            new_name='lugar_seguimiento',
        ),
    ]
