from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seguimiento', '0007_seguimiento_lugar_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='indicacionmedica',
            name='visible_padre',
            field=models.BooleanField(
                default=True,
                help_text='Permite mostrar esta indicación en el Portal Padres.',
                verbose_name='Visible para padre/tutor',
            ),
        ),
    ]
