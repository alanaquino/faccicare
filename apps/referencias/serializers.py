from rest_framework import serializers

from .models import ReferenciaMedica


class ReferenciaMedicaSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    centro_origen = serializers.CharField(source='medico_referente.centro_medico', read_only=True)
    centro_destino = serializers.CharField(source='hospital_destino', read_only=True)

    class Meta:
        model = ReferenciaMedica
        fields = (
            'id',
            'paciente',
            'paciente_nombre',
            'centro_origen',
            'centro_destino',
            'prioridad',
            'estado',
            'motivo_referencia',
            'fecha_referencia',
        )
