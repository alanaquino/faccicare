from rest_framework import serializers
from .models import CentroSalud, LogActividad

class CentroSaludSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroSalud
        fields = '__all__'

class LogActividadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogActividad
        fields = '__all__'
