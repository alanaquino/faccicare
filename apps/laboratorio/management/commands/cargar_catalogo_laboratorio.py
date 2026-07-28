from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.laboratorio.catalogo_laboratorio import CATALOGO_LABORATORIO
from apps.laboratorio.models import CatalogoEstudio, CatalogoParametro


def _decimal_or_none(value):
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value).replace(',', '.'))
    except (InvalidOperation, ValueError):
        return None


class Command(BaseCommand):
    help = 'Carga o actualiza el catalogo clinico de laboratorio pediatrico oncologico.'

    @transaction.atomic
    def handle(self, *args, **options):
        estudios_creados = 0
        estudios_actualizados = 0
        parametros_creados = 0
        parametros_actualizados = 0

        for estudio_data in CATALOGO_LABORATORIO:
            estudio, creado = CatalogoEstudio.objects.update_or_create(
                nombre=estudio_data['nombre'],
                defaults={
                    'categoria': estudio_data.get('categoria', ''),
                    'descripcion': estudio_data.get('descripcion', ''),
                    'activo': estudio_data.get('activo', True),
                },
            )
            if creado:
                estudios_creados += 1
            else:
                estudios_actualizados += 1

            for parametro_orden, parametro_data in enumerate(estudio_data.get('parametros', []), start=1):
                tipo_valor = parametro_data.get('tipo_valor', CatalogoParametro.TipoValor.NUMERICO)
                _, creado = CatalogoParametro.objects.update_or_create(
                    estudio=estudio,
                    nombre=parametro_data['nombre'],
                    defaults={
                        'unidad': parametro_data.get('unidad', ''),
                        'referencia_minima': _decimal_or_none(parametro_data.get('min')),
                        'referencia_maxima': _decimal_or_none(parametro_data.get('max')),
                        'referencia_texto': parametro_data.get('referencia_texto', ''),
                        'requiere_comentario': parametro_data.get('requiere_comentario', False),
                        'comentario_sugerido': parametro_data.get('comentario_sugerido', ''),
                        'alerta_sistema': parametro_data.get('alerta_sistema', ''),
                        'alerta_critica': parametro_data.get('alerta_critica', False),
                        'tipo_valor': tipo_valor,
                        'activo': parametro_data.get('activo', True),
                        'orden': parametro_data.get('orden', parametro_orden),
                    },
                )
                if creado:
                    parametros_creados += 1
                else:
                    parametros_actualizados += 1

        total_estudios = CatalogoEstudio.objects.filter(
            nombre__in=[item['nombre'] for item in CATALOGO_LABORATORIO]
        ).count()
        nombres_parametros = [
            (estudio['nombre'], parametro['nombre'])
            for estudio in CATALOGO_LABORATORIO
            for parametro in estudio.get('parametros', [])
        ]
        total_parametros = 0
        for estudio_nombre, parametro_nombre in nombres_parametros:
            total_parametros += CatalogoParametro.objects.filter(
                estudio__nombre=estudio_nombre, nombre=parametro_nombre
            ).count()

        self.stdout.write(
            self.style.SUCCESS(
                'Catalogo de laboratorio cargado: '
                f'{total_estudios} estudios, {total_parametros} parametros. '
                f'Estudios creados/actualizados: {estudios_creados}/{estudios_actualizados}. '
                f'Parametros creados/actualizados: {parametros_creados}/{parametros_actualizados}.'
            )
        )
