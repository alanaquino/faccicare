from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notificaciones', '0004_alter_notificacion_options_and_more'),
    ]

    operations = [
        migrations.DeleteModel(name='AdjuntoMensaje'),
        migrations.DeleteModel(name='ParticipanteConversacion'),
        migrations.DeleteModel(name='Mensaje'),
        migrations.DeleteModel(name='Conversacion'),
    ]
