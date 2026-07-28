from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone

from apps.auth_app.models import CustomUser
from .models import CuestionarioCribado


class CuestionarioCribadoSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    medico_nombre = serializers.CharField(source='medico.get_full_name', read_only=True)
    sintomas_presentes = serializers.SerializerMethodField()

    class Meta:
        model = CuestionarioCribado
        fields = [
            'id',
            'paciente',
            'paciente_nombre',
            'medico',
            'medico_nombre',
            'fecha_evaluacion',
            'puntaje_total',
            'nivel_riesgo',
            'resultado',
            'requiere_referencia',
            'observaciones',
            'sintomas_presentes',
        ]
        read_only_fields = ['id', 'fecha_evaluacion', 'puntaje_total', 'nivel_riesgo', 'resultado']

    def get_sintomas_presentes(self, obj):
        return [
            campo for campo in CuestionarioCribado.CAMPOS_SINTOMAS
            if getattr(obj, campo)
        ]


class CuestionarioCribadoViewSet(viewsets.ModelViewSet):
    serializer_class = CuestionarioCribadoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'rol'):
            return CuestionarioCribado.objects.none()

        if user.rol == CustomUser.Rol.ADMIN:
            return CuestionarioCribado.objects.select_related('paciente', 'medico')

        if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
            return CuestionarioCribado.objects.filter(
                Q(paciente__medico_asignado=user) | Q(paciente__creado_por=user)
            ).select_related('paciente', 'medico')

        if user.rol == CustomUser.Rol.ONCOLOGO:
            return CuestionarioCribado.objects.filter(
                paciente__referencias__especialista_destino=user
            ).distinct().select_related('paciente', 'medico')

        return CuestionarioCribado.objects.none()

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        queryset = self.get_queryset()
        return Response({
            'total': queryset.count(),
            'riesgo_alto': queryset.filter(nivel_riesgo='ALTO').count(),
            'riesgo_medio': queryset.filter(nivel_riesgo='MEDIO').count(),
            'riesgo_bajo': queryset.filter(nivel_riesgo='BAJO').count(),
            'requieren_referencia': queryset.filter(requiere_referencia=True).count(),
        })

    @action(detail=False, methods=['get'])
    def tendencia(self, request):
        queryset = self.get_queryset()
        ultimos_7_dias = timezone.now() - timezone.timedelta(days=7)
        ultimas_2_semanas = timezone.now() - timezone.timedelta(days=14)

        return Response({
            'ultimos_7_dias': queryset.filter(fecha_evaluacion__gte=ultimos_7_dias).count(),
            'ultimas_2_semanas': queryset.filter(fecha_evaluacion__gte=ultimas_2_semanas).count(),
            'riesgo_alto_reciente': queryset.filter(
                nivel_riesgo='ALTO',
                fecha_evaluacion__gte=ultimos_7_dias
            ).count(),
        })

    @action(detail=False, methods=['get'])
    def por_paciente(self, request):
        paciente_id = request.query_params.get('paciente_id')
        if not paciente_id:
            return Response({'error': 'paciente_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset().filter(paciente_id=paciente_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        queryset = self.get_queryset()

        por_medico = queryset.values('medico__first_name', 'medico__last_name').annotate(
            total=Count('id'),
            alto=Count('id', filter=Q(nivel_riesgo='ALTO'))
        )

        por_nivel = queryset.values('nivel_riesgo').annotate(total=Count('id'))

        return Response({
            'por_medico': list(por_medico),
            'por_nivel': list(por_nivel),
            'total_evaluaciones': queryset.count(),
        })
