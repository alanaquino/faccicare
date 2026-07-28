from rest_framework import serializers

from .models import SeguimientoPaciente


class SeguimientoPacienteSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    responsable = serializers.CharField(source='medico.nombre_completo', read_only=True)

    class Meta:
        model = SeguimientoPaciente
        fields = (
            'id',
            'paciente',
            'paciente_nombre',
            'estado_clinico',
            'sintomas_actuales',
            'observaciones',
            'proxima_fecha_seguimiento',
            'responsable',
            'fecha_seguimiento',
            'requiere_hospitalizacion',
        )


class AlertaClinicaSerializer(serializers.Serializer):
    paciente = serializers.CharField(source='paciente.nombre_completo')
    tipo = serializers.CharField()
    nivel = serializers.CharField()
    atendida = serializers.BooleanField()
    fecha = serializers.DateTimeField()
    mensaje = serializers.CharField()
