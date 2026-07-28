# Generated manually because the local SQLite migration history is inconsistent.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pacientes", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NotaClinica",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tipo", models.CharField(choices=[("EVOLUCION", "Evolucion"), ("DIAGNOSTICO", "Diagnostico"), ("TRATAMIENTO", "Tratamiento"), ("OBSERVACION", "Observacion"), ("ALERTA", "Alerta clinica")], db_index=True, default="EVOLUCION", max_length=20, verbose_name="Tipo de nota")),
                ("texto", models.TextField(verbose_name="Nota clinica")),
                ("es_importante", models.BooleanField(default=False, verbose_name="Marcar como importante")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Registrada el")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizada el")),
                ("autor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notas_clinicas_creadas", to=settings.AUTH_USER_MODEL, verbose_name="Autor")),
                ("paciente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notas_clinicas", to="pacientes.paciente", verbose_name="Paciente")),
            ],
            options={
                "verbose_name": "Nota clinica",
                "verbose_name_plural": "Notas clinicas",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["paciente"], name="nota_paciente_idx"),
                    models.Index(fields=["tipo"], name="nota_tipo_idx"),
                    models.Index(fields=["created_at"], name="nota_fecha_idx"),
                ],
            },
        ),
    ]
