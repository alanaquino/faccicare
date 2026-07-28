from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from apps.auth_app.models import CustomUser
from .models import CasoClinico, NotaCaso
from .serializers import CasoClinicoSerializer, CasoClinicoListSerializer, NotaCasoSerializer


class CasoClinicoViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['codigo_caso', 'titulo', 'paciente__nombres', 'paciente__apellidos']
    ordering_fields    = ['created_at', 'fecha_apertura', 'prioridad', 'estado']
    ordering           = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.rol == CustomUser.Rol.ADMIN:
            qs = CasoClinico.objects.all()
        elif user.rol == CustomUser.Rol.ONCOLOGO:
            qs = CasoClinico.objects.filter(
                Q(medico_responsable=user) |
                Q(paciente__referencias__especialista_destino=user)
            ).distinct()
        elif user.rol in [CustomUser.Rol.MEDICO, CustomUser.Rol.PEDIATRA]:
            qs = CasoClinico.objects.filter(
                Q(medico_responsable=user) |
                Q(paciente__medico_asignado=user)
            ).distinct()
        else:
            qs = CasoClinico.objects.all()

        estado    = self.request.query_params.get('estado')
        tipo      = self.request.query_params.get('tipo_cancer')
        prioridad = self.request.query_params.get('prioridad')
        paciente  = self.request.query_params.get('paciente')

        if estado:
            qs = qs.filter(estado=estado)
        if tipo:
            qs = qs.filter(tipo_cancer=tipo)
        if prioridad:
            qs = qs.filter(prioridad=prioridad)
        if paciente:
            qs = qs.filter(paciente__id=paciente)

        return qs.select_related('paciente', 'medico_responsable')

    def get_serializer_class(self):
        if self.action == 'list':
            return CasoClinicoListSerializer
        return CasoClinicoSerializer

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    @action(detail=True, methods=['get'])
    def notas(self, request, pk=None):
        caso  = self.get_object()
        notas = caso.notas.select_related('autor').order_by('-created_at')
        serializer = NotaCasoSerializer(notas, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='notas/agregar')
    def agregar_nota(self, request, pk=None):
        caso = self.get_object()
        serializer = NotaCasoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(caso=caso, autor=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def por_paciente(self, request):
        paciente_id = request.query_params.get('paciente_id')
        if not paciente_id:
            return Response({'error': 'paciente_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)
        casos = self.get_queryset().filter(paciente__id=paciente_id)
        serializer = CasoClinicoListSerializer(casos, many=True)
        return Response(serializer.data)
