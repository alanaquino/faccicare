from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_app', '0002_cedula_null_true'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='rol',
            field=models.CharField(
                choices=[
                    ('ADMIN', 'Administrador'),
                    ('MEDICO', 'Médico General'),
                    ('PEDIATRA', 'Pediatra'),
                    ('ONCOLOGO', 'Oncólogo'),
                    ('PERSONAL_FACCI', 'Coordinador FACCI'),
                    ('TRABAJADORA_SOCIAL', 'Trabajo Social / Psicología'),
                    ('ENFERMERA', 'Enfermera / Técnico de Salud'),
                    ('PADRE_TUTOR', 'Padre / Tutor'),
                ],
                db_index=True,
                default='MEDICO',
                max_length=25,
                verbose_name='Rol',
            ),
        ),
    ]
