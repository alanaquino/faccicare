from rest_framework import serializers

from .models import Notificacion


class NotificacionSerializer(serializers.ModelSerializer):
    icono = serializers.CharField(read_only=True)
    color = serializers.CharField(read_only=True)
    tiempo = serializers.CharField(read_only=True)

    class Meta:
        model = Notificacion
        fields = [
            'id', 'tipo', 'modulo', 'prioridad', 'titulo', 'mensaje',
            'leida', 'fecha_lectura', 'accion_url', 'accion_texto',
            'archivada', 'icono', 'color', 'tiempo', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'fecha_lectura']
