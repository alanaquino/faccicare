from rest_framework import serializers

from .models import Paciente


class PacienteSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    tutor = serializers.CharField(source='padre_tutor.usuario.nombre_completo', read_only=True)
    telefono_tutor = serializers.CharField(source='padre_tutor.usuario.telefono', read_only=True)
    centro_salud = serializers.CharField(source='medico_asignado.centro_medico', read_only=True)

    class Meta:
        model = Paciente
        fields = (
            'id',
            'codigo_paciente',
            'nombres',
            'apellidos',
            'nombre_completo',
            'fecha_nacimiento',
            'sexo',
            'tutor',
            'telefono_tutor',
            'centro_salud',
            'estado_actual',
            'created_at',
        )
