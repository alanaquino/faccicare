from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('casos', '0001_initial'),
        ('dashboard', '0002_remove_alertaclinica_caso'),
    ]

    operations = [
        migrations.DeleteModel(name='NotaCaso'),
        migrations.DeleteModel(name='CasoClinico'),
    ]
