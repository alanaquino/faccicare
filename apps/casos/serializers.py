from rest_framework import serializers
from .models import CasoClinico, NotaCaso


class NotaCasoSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.ReadOnlyField()
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    fecha        = serializers.ReadOnlyField()
    color        = serializers.ReadOnlyField()
    icono        = serializers.ReadOnlyField()

    class Meta:
        model  = NotaCaso
        fields = [
            'id', 'tipo', 'tipo_display', 'titulo', 'contenido',
            'es_importante', 'autor_nombre', 'fecha', 'color', 'icono',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CasoClinicoSerializer(serializers.ModelSerializer):
    paciente_nombre    = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    medico_nombre      = serializers.CharField(source='medico_responsable.get_full_name', read_only=True)
    estado_display     = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_display       = serializers.CharField(source='get_tipo_cancer_display', read_only=True)
    prioridad_display  = serializers.CharField(source='get_prioridad_display', read_only=True)
    estado_color       = serializers.ReadOnlyField()
    prioridad_color    = serializers.ReadOnlyField()
    dias_abierto       = serializers.ReadOnlyField()
    total_notas        = serializers.ReadOnlyField()
    notas              = NotaCasoSerializer(many=True, read_only=True)

    class Meta:
        model  = CasoClinico
        fields = [
            'id', 'codigo_caso', 'paciente', 'paciente_nombre',
            'medico_responsable', 'medico_nombre',
            'tipo_cancer', 'tipo_display',
            'estado', 'estado_display', 'estado_color',
            'prioridad', 'prioridad_display', 'prioridad_color',
            'titulo', 'resumen_clinico', 'protocolo_tratamiento', 'observaciones',
            'fecha_apertura', 'fecha_cierre',
            'dias_abierto', 'total_notas', 'notas',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'codigo_caso', 'created_at', 'updated_at']


class CasoClinicoListSerializer(serializers.ModelSerializer):
    paciente_nombre   = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    medico_nombre     = serializers.CharField(source='medico_responsable.get_full_name', read_only=True)
    estado_display    = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_display      = serializers.CharField(source='get_tipo_cancer_display', read_only=True)
    prioridad_display = serializers.CharField(source='get_prioridad_display', read_only=True)
    estado_color      = serializers.ReadOnlyField()
    prioridad_color   = serializers.ReadOnlyField()
    total_notas       = serializers.ReadOnlyField()

    class Meta:
        model  = CasoClinico
        fields = [
            'id', 'codigo_caso', 'paciente_nombre', 'medico_nombre',
            'tipo_cancer', 'tipo_display',
            'estado', 'estado_display', 'estado_color',
            'prioridad', 'prioridad_display', 'prioridad_color',
            'titulo', 'fecha_apertura', 'total_notas', 'created_at',
        ]
