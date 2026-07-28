import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cribado', '0001_initial'),
        ('pacientes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CasoClinico',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('codigo_caso', models.CharField(db_index=True, help_text='Generado automáticamente (ej. CASO-2026-0001)', max_length=20, unique=True, verbose_name='Código del caso')),
                ('tipo_cancer', models.CharField(choices=[('LEUCEMIA', 'Leucemia'), ('TUMORES_SNC', 'Tumores del SNC'), ('RETINOBLASTOMA', 'Retinoblastoma'), ('TUMOR_WILMS', 'Tumor de Wilms'), ('NEUROBLASTOMA', 'Neuroblastoma'), ('LINFOMA', 'Linfoma'), ('SARCOMA', 'Sarcoma'), ('OTRO', 'Otro / Por definir')], db_index=True, default='OTRO', max_length=20, verbose_name='Tipo de cáncer')),
                ('estado', models.CharField(choices=[('ABIERTO', 'Abierto'), ('EN_ESTUDIO', 'En estudio'), ('EN_TRATAMIENTO', 'En tratamiento'), ('EN_REMISION', 'En remisión'), ('CERRADO', 'Cerrado'), ('ARCHIVADO', 'Archivado')], db_index=True, default='ABIERTO', max_length=20, verbose_name='Estado del caso')),
                ('prioridad', models.CharField(choices=[('BAJA', 'Baja'), ('MEDIA', 'Media'), ('ALTA', 'Alta'), ('URGENTE', 'Urgente')], db_index=True, default='MEDIA', max_length=10, verbose_name='Prioridad')),
                ('titulo', models.CharField(help_text='Descripción clínica breve que identifica el caso', max_length=250, verbose_name='Título del caso')),
                ('resumen_clinico', models.TextField(help_text='Descripción del cuadro clínico, síntomas principales y hallazgos relevantes', verbose_name='Resumen clínico')),
                ('protocolo_tratamiento', models.TextField(blank=True, help_text='Protocolo oncológico asignado y descripción del plan terapéutico', verbose_name='Protocolo de tratamiento')),
                ('observaciones', models.TextField(blank=True, verbose_name='Observaciones adicionales')),
                ('fecha_apertura', models.DateField(verbose_name='Fecha de apertura')),
                ('fecha_cierre', models.DateField(blank=True, null=True, verbose_name='Fecha de cierre')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Registrado el')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Actualizado el')),
                ('creado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='casos_creados', to=settings.AUTH_USER_MODEL, verbose_name='Creado por')),
                ('cribado_origen', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='casos_derivados', to='cribado.cuestionariocribado', verbose_name='Cribado de origen')),
                ('medico_responsable', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='casos_a_cargo', to=settings.AUTH_USER_MODEL, verbose_name='Médico responsable')),
                ('paciente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='casos_clinicos', to='pacientes.paciente', verbose_name='Paciente')),
            ],
            options={
                'verbose_name': 'Caso clínico',
                'verbose_name_plural': 'Casos clínicos',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='NotaCaso',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('tipo', models.CharField(choices=[('EVOLUCION', 'Evolución clínica'), ('DIAGNOSTICO', 'Diagnóstico / Hallazgo'), ('TRATAMIENTO', 'Tratamiento / Protocolo'), ('INTERCONSULTA', 'Interconsulta'), ('LABORATORIO', 'Resultado de laboratorio'), ('IMAGEN', 'Imagen médica'), ('QUIRURGICO', 'Procedimiento quirúrgico'), ('ALTA', 'Alta / Egreso'), ('CIERRE', 'Cierre del caso'), ('OBSERVACION', 'Observación general')], db_index=True, default='EVOLUCION', max_length=20, verbose_name='Tipo de nota')),
                ('titulo', models.CharField(max_length=250, verbose_name='Título')),
                ('contenido', models.TextField(verbose_name='Contenido')),
                ('es_importante', models.BooleanField(default=False, verbose_name='Marcar como importante')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Registrada el')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Actualizada el')),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='notas_casos', to=settings.AUTH_USER_MODEL, verbose_name='Autor')),
                ('caso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notas', to='casos.casoclinico', verbose_name='Caso clínico')),
            ],
            options={
                'verbose_name': 'Nota del caso',
                'verbose_name_plural': 'Notas del caso',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='casoclinico',
            index=models.Index(fields=['paciente'], name='caso_paciente_idx'),
        ),
        migrations.AddIndex(
            model_name='casoclinico',
            index=models.Index(fields=['estado'], name='caso_estado_idx'),
        ),
        migrations.AddIndex(
            model_name='casoclinico',
            index=models.Index(fields=['prioridad'], name='caso_prioridad_idx'),
        ),
        migrations.AddIndex(
            model_name='casoclinico',
            index=models.Index(fields=['tipo_cancer'], name='caso_tipo_idx'),
        ),
        migrations.AddIndex(
            model_name='casoclinico',
            index=models.Index(fields=['fecha_apertura'], name='caso_fecha_apertura_idx'),
        ),
        migrations.AddIndex(
            model_name='casoclinico',
            index=models.Index(fields=['medico_responsable'], name='caso_medico_idx'),
        ),
        migrations.AddIndex(
            model_name='notacaso',
            index=models.Index(fields=['caso'], name='nota_caso_idx'),
        ),
        migrations.AddIndex(
            model_name='notacaso',
            index=models.Index(fields=['tipo'], name='nota_caso_tipo_idx'),
        ),
        migrations.AddIndex(
            model_name='notacaso',
            index=models.Index(fields=['autor'], name='nota_caso_autor_idx'),
        ),
    ]
