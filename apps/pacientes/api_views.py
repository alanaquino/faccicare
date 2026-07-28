from rest_framework import viewsets

from .models import Paciente
from .serializers import PacienteSerializer


class PacienteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Paciente.objects.select_related('padre_tutor__usuario', 'medico_asignado')
    serializer_class = PacienteSerializer
    search_fields = ('nombres', 'apellidos', 'codigo_paciente', 'provincia')
    ordering_fields = ('created_at', 'nombres', 'apellidos')
    ordering = ('-created_at',)
