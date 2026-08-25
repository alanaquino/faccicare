# Generated manually for CU-20 clinical note attachments.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pacientes', '0005_alter_paciente_alergias_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='notaclinica',
            name='adjunto',
            field=models.FileField(
                blank=True,
                help_text='Archivo opcional asociado a la nota clinica',
                null=True,
                upload_to='notas_clinicas/%Y/%m/',
                verbose_name='Adjunto',
            ),
        ),
    ]
