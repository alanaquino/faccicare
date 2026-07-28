from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
        ('casos', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='alertaclinica',
            name='caso',
        ),
    ]
