from django.utils import timezone
from rest_framework import filters, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Notificacion
from .serializers import NotificacionSerializer


class NotificacionListView(generics.ListAPIView):
    serializer_class = NotificacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['titulo', 'mensaje', 'tipo']

    def get_queryset(self):
        qs = Notificacion.objects.filter(usuario=self.request.user)
        leida = self.request.query_params.get('leida')
        archivada = self.request.query_params.get('archivada')
        tipo = self.request.query_params.get('tipo')
        if leida is not None:
            qs = qs.filter(leida=(leida.lower() == 'true'))
        if archivada is not None:
            qs = qs.filter(archivada=(archivada.lower() == 'true'))
        else:
            qs = qs.filter(archivada=False)
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def marcar_notificacion_leida_api(request, pk):
    notif = generics.get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    notif.marcar_como_leida()
    return Response({'status': 'ok'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def marcar_todas_leidas_api(request):
    updated = Notificacion.objects.filter(
        usuario=request.user, leida=False, archivada=False
    ).update(leida=True, fecha_lectura=timezone.now())
    return Response({'actualizadas': updated})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def conteo_no_leidas(request):
    sin_leer = Notificacion.objects.filter(
        usuario=request.user, leida=False, archivada=False
    ).count()
    return Response({'sin_leer': sin_leer})
