from django.core.management.base import BaseCommand
from django.db import transaction

from apps.padres.models import RecursoEducativo
from apps.padres.recursos_data import RECURSOS_FAMILIA


class Command(BaseCommand):
    help = 'Crea o actualiza las guías educativas del portal de familias sin duplicarlas.'

    @transaction.atomic
    def handle(self, *args, **options):
        creados = 0
        actualizados = 0

        for datos in RECURSOS_FAMILIA:
            valores = {
                'descripcion': datos['descripcion_corta'],
                'imagen': 'img/portal_padres_bg.jpg',
                'video_url': '',
                'url': '',
                'activo': True,
                **datos,
            }
            slug = valores.pop('slug')
            recurso = (
                RecursoEducativo.objects.filter(slug=slug).first()
                or RecursoEducativo.objects.filter(titulo=valores['titulo']).first()
            )
            fue_creado = recurso is None
            if fue_creado:
                recurso = RecursoEducativo(slug=slug)
            else:
                recurso.slug = slug

            for campo, valor in valores.items():
                setattr(recurso, campo, valor)
            recurso.save()
            if fue_creado:
                creados += 1
            else:
                actualizados += 1

            self.stdout.write(f'  - {recurso.titulo}')

        self.stdout.write(self.style.SUCCESS(
            f'Recursos para la familia listos: {creados} creados, '
            f'{actualizados} actualizados.'
        ))
