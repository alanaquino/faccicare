from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth_app.models import CustomUser
from apps.dashboard.views import _centros_salud_data, _dashboard_data
from apps.core.geocoding import guardar_geocodificacion_centro
from apps.core.models import CentroSalud


class CoreAPIView(APIView):
    def get(self, request):
        return Response(
            {
                'sistema': 'FACCI Care',
                'dashboard': _dashboard_data(request.user),
                'centros_salud': _centros_salud_data(),
            }
        )


def _centro_mapa_payload(centro):
    return {
        'id': centro.id,
        'nombre': centro.nombre,
        'tipo': centro.tipo,
        'tipo_display': centro.get_tipo_display(),
        'provincia': centro.provincia,
        'municipio': centro.municipio,
        'direccion': centro.direccion,
        'telefono': centro.telefono,
        'latitud': centro.latitud,
        'longitud': centro.longitud,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def centros_salud_mapa_view(request):
    centros = (
        CentroSalud.objects
        .filter(activo=True, latitud__isnull=False, longitud__isnull=False)
        .order_by('nombre')
    )
    return Response([_centro_mapa_payload(centro) for centro in centros])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def geocodificar_centro_salud_view(request, pk):
    if getattr(request.user, 'rol', None) != CustomUser.Rol.ADMIN:
        return Response(
            {
                'ok': False,
                'mensaje': 'No tiene permiso para actualizar coordenadas.',
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    centro = get_object_or_404(CentroSalud, pk=pk)
    if guardar_geocodificacion_centro(centro):
        return Response(
            {
                'ok': True,
                'mensaje': 'Coordenadas actualizadas correctamente',
                'latitud': centro.latitud,
                'longitud': centro.longitud,
            }
        )

    return Response(
        {
            'ok': False,
            'mensaje': 'No se pudieron encontrar coordenadas para este centro',
        },
        status=status.HTTP_404_NOT_FOUND,
    )
