from rest_framework import viewsets
from rest_framework.response import Response

from apps.dashboard.views import _alertas_data
from apps.referencias.models import ReferenciaMedica
from apps.referencias.serializers import ReferenciaMedicaSerializer

from .models import SeguimientoPaciente
from .serializers import AlertaClinicaSerializer, SeguimientoPacienteSerializer


class ReferenciaMedicaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReferenciaMedica.objects.select_related(
        'paciente',
        'medico_referente',
        'especialista_destino',
    )
    serializer_class = ReferenciaMedicaSerializer
    search_fields = ('paciente__nombres', 'paciente__apellidos', 'motivo_referencia')
    ordering_fields = ('fecha_referencia', 'prioridad', 'estado')
    ordering = ('-fecha_referencia',)


class SeguimientoPacienteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SeguimientoPaciente.objects.select_related('paciente', 'medico')
    serializer_class = SeguimientoPacienteSerializer
    search_fields = ('paciente__nombres', 'paciente__apellidos', 'estado_clinico')
    ordering_fields = ('fecha_seguimiento', 'proxima_fecha_seguimiento')
    ordering = ('-fecha_seguimiento',)


class AlertaClinicaViewSet(viewsets.ViewSet):
    def list(self, request):
        serializer = AlertaClinicaSerializer(_alertas_data(), many=True)
        return Response(serializer.data)
