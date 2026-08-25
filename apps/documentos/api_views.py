from django_filters import rest_framework as filters
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.utils import timezone

from apps.auth_app.models import CustomUser
from apps.pacientes.models import Paciente
from .models import DocumentoMedico, SolicitudDocumento
from .serializers import (
    DocumentoMedicoListSerializer, DocumentoMedicoDetailSerializer,
    DocumentoMedicoCreateSerializer, SolicitudDocumentoListSerializer,
    SolicitudDocumentoDetailSerializer, SolicitudDocumentoCreateSerializer
)


class DocumentoMedicoFilter(filters.FilterSet):
    fecha_desde = filters.DateFilter(field_name='fecha_documento', lookup_expr='gte')
    fecha_hasta = filters.DateFilter(field_name='fecha_documento', lookup_expr='lte')
    paciente = filters.CharFilter(field_name='paciente__nombre_completo', lookup_expr='icontains')

    class Meta:
        model = DocumentoMedico
        fields = ['tipo_documento', 'estado', 'paciente']


class DocumentoMedicoViewSet(viewsets.ModelViewSet):
    queryset = DocumentoMedico.objects.all()
    parser_classes = (MultiPartParser, FormParser)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = DocumentoMedicoFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentoMedicoCreateSerializer
        elif self.action == 'retrieve':
            return DocumentoMedicoDetailSerializer
        return DocumentoMedicoListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = DocumentoMedico.objects.select_related('paciente', 'subido_por')

        if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
            qs = qs.filter(
                Q(paciente__medico_asignado=user) | Q(paciente__creado_por=user)
            )
        elif user.rol == CustomUser.Rol.ONCOLOGO:
            qs = qs.filter(paciente__referencias__especialista_destino=user).distinct()
        elif user.rol != CustomUser.Rol.ADMIN:
            return DocumentoMedico.objects.none()

        return qs.order_by('-fecha_documento')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        paciente = Paciente.objects.get(id=serializer.validated_data['paciente'].id)
        user = request.user

        if not self._puede_subir_documento(user, paciente):
            return Response(
                {'detail': 'No tienes permiso para subir documentos para este paciente.'},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _puede_subir_documento(self, user, paciente):
        if user.rol == CustomUser.Rol.ADMIN:
            return True
        if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
            return (paciente.medico_asignado == user or paciente.creado_por == user)
        if user.rol == CustomUser.Rol.ONCOLOGO:
            return paciente.referencias.filter(especialista_destino=user).exists()
        return False

    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        documento = self.get_object()
        nuevo_estado = request.data.get('estado')

        if nuevo_estado not in dict(DocumentoMedico.EstadoDocumento.choices):
            return Response(
                {'detail': f'Estado inválido: {nuevo_estado}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not self._puede_modificar_documento(request.user, documento):
            return Response(
                {'detail': 'No tienes permiso para modificar este documento.'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        observaciones = request.data.get('observaciones', '').strip()
        if nuevo_estado == DocumentoMedico.EstadoDocumento.CORRECCION and not observaciones:
            return Response(
                {'detail': 'Debe ingresar las observaciones antes de marcar que requiere corrección.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        documento.estado = nuevo_estado
        if observaciones:
            documento.descripcion = f"{documento.descripcion}\n[Observación de corrección]: {observaciones}".strip()
        documento.save(update_fields=['estado', 'descripcion', 'updated_at'])

        serializer = self.get_serializer(documento)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_paciente(self, request):
        paciente_id = request.query_params.get('paciente_id')
        if not paciente_id:
            return Response(
                {'detail': 'Parámetro paciente_id requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            return Response(
                {'detail': 'Paciente no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        qs = self.get_queryset().filter(paciente=paciente)
        serializer = DocumentoMedicoListSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def resumen_estadisticas(self, request):
        qs = self.get_queryset()
        return Response({
            'total': qs.count(),
            'pendientes': qs.filter(estado=DocumentoMedico.EstadoDocumento.PENDIENTE).count(),
            'revisados': qs.filter(estado=DocumentoMedico.EstadoDocumento.REVISADO).count(),
            'correccion': qs.filter(estado=DocumentoMedico.EstadoDocumento.CORRECCION).count(),
            'por_tipo': dict(qs.values_list('tipo_documento').annotate(
                count=filters.Count('id')
            ).values_list('tipo_documento', 'count')),
        })

    def _puede_modificar_documento(self, user, documento):
        if user.rol == CustomUser.Rol.ADMIN:
            return True
        if documento.subido_por == user:
            return True
        if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
            return (documento.paciente.medico_asignado == user or
                    documento.paciente.creado_por == user)
        return False

    @action(detail=True, methods=['post'])
    def duplicar(self, request, pk=None):
        documento = self.get_object()

        if not self._puede_subir_documento(request.user, documento.paciente):
            return Response(
                {'detail': 'No tienes permiso'},
                status=status.HTTP_403_FORBIDDEN
            )

        nuevo_doc = DocumentoMedico.objects.create(
            paciente=documento.paciente,
            subido_por=request.user,
            tipo_documento=documento.tipo_documento,
            archivo=documento.archivo,
            descripcion=f"{documento.descripcion} (Duplicado)",
            fecha_documento=documento.fecha_documento,
        )

        serializer = self.get_serializer(nuevo_doc)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SolicitudDocumentoViewSet(viewsets.ModelViewSet):
    queryset = SolicitudDocumento.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return SolicitudDocumentoCreateSerializer
        elif self.action == 'retrieve':
            return SolicitudDocumentoDetailSerializer
        return SolicitudDocumentoListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = SolicitudDocumento.objects.select_related(
            'paciente', 'medico_solicitante', 'documento_asociado'
        )

        if user.rol in [CustomUser.Rol.PEDIATRA, CustomUser.Rol.MEDICO]:
            qs = qs.filter(
                Q(paciente__medico_asignado=user) |
                Q(paciente__creado_por=user) |
                Q(medico_solicitante=user)
            )
        elif user.rol == CustomUser.Rol.ONCOLOGO:
            qs = qs.filter(
                Q(paciente__referencias__especialista_destino=user) |
                Q(medico_solicitante=user)
            ).distinct()
        elif user.rol != CustomUser.Rol.ADMIN:
            qs = SolicitudDocumento.objects.none()

        return qs.order_by('-created_at')

    @action(detail=True, methods=['post'])
    def asociar_documento(self, request, pk=None):
        solicitud = self.get_object()
        documento_id = request.data.get('documento_id')

        try:
            documento = DocumentoMedico.objects.get(id=documento_id)
        except DocumentoMedico.DoesNotExist:
            return Response(
                {'detail': 'Documento no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

        if documento.paciente != solicitud.paciente:
            return Response(
                {'detail': 'El documento debe ser del mismo paciente'},
                status=status.HTTP_400_BAD_REQUEST
            )

        solicitud.documento_asociado = documento
        solicitud.estado = SolicitudDocumento.EstadoSolicitud.SUBIDO
        solicitud.save()

        serializer = self.get_serializer(solicitud)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cambiar_estado(self, request, pk=None):
        solicitud = self.get_object()
        nuevo_estado = request.data.get('estado')

        if nuevo_estado not in dict(SolicitudDocumento.EstadoSolicitud.choices):
            return Response(
                {'detail': f'Estado inválido: {nuevo_estado}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user.rol not in [CustomUser.Rol.ADMIN, CustomUser.Rol.PEDIATRA,
                                     CustomUser.Rol.MEDICO, CustomUser.Rol.ONCOLOGO]:
            return Response(
                {'detail': 'No tienes permiso'},
                status=status.HTTP_403_FORBIDDEN
            )

        solicitud.estado = nuevo_estado
        solicitud.save(update_fields=['estado', 'updated_at'])

        serializer = self.get_serializer(solicitud)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        qs = self.get_queryset().filter(
            estado=SolicitudDocumento.EstadoSolicitud.PENDIENTE
        )
        serializer = SolicitudDocumentoListSerializer(qs, many=True)
        return Response(serializer.data)
