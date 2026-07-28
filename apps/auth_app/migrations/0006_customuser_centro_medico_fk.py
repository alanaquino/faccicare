from django.db import migrations, models
import django.db.models.deletion

from apps.core.centros_matching import match_centro_por_nombre


def poblar(apps, schema_editor):
    CustomUser = apps.get_model('auth_app', 'CustomUser')
    CentroSalud = apps.get_model('core', 'CentroSalud')
    for user in CustomUser.objects.all():
        centro = match_centro_por_nombre(CentroSalud, user.centro_medico)
        if centro is not None:
            user.centro_medico_fk_id = centro.id
            user.save(update_fields=['centro_medico_fk'])


def revertir(apps, schema_editor):
    CustomUser = apps.get_model('auth_app', 'CustomUser')
    for user in CustomUser.objects.all():
        if user.centro_medico_fk_id:
            user.centro_medico = user.centro_medico_fk.nombre
            user.save(update_fields=['centro_medico'])


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0005_customuser_tipo_documento'),
        ('core', '0007_sistemaconfiguracion_logo_aplicacion_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='centro_medico_fk',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='usuarios',
                to='core.centrosalud',
                verbose_name='Centro médico',
                help_text='Hospital o clínica donde labora',
            ),
        ),
        migrations.RunPython(poblar, revertir),
        migrations.RemoveField(model_name='customuser', name='centro_medico'),
        migrations.RenameField(
            model_name='customuser',
            old_name='centro_medico_fk',
            new_name='centro_medico',
        ),
    ]
