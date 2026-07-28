"""
Comando de migración de datos desde SQLite hacia MySQL.

Uso:
  1. Configura las variables DB_* en .env apuntando a MySQL.
  2. Ejecuta: python manage.py migrate_to_mysql

El comando exporta todos los datos desde SQLite, configura MySQL,
aplica las migraciones y carga los datos exportados.
"""
import json
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = 'Migra datos desde SQLite a MySQL. Requiere DB_ENGINE=mysql en .env.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dump-file',
            default='sqlite_dump.json',
            help='Ruta del archivo JSON temporal para el dump (default: sqlite_dump.json)',
        )
        parser.add_argument(
            '--skip-dump',
            action='store_true',
            help='Omite la exportación de datos (usa un dump existente)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra los pasos sin ejecutarlos',
        )

    def handle(self, *args, **options):
        dump_path = Path(options['dump_file'])
        dry_run = options['dry_run']

        self.stdout.write(self.style.WARNING('=== Migración SQLite → MySQL ===\n'))

        # ── Paso 1: Validar configuración de MySQL ────────────────────────────
        db_cfg = settings.DATABASES['default']
        if 'mysql' not in db_cfg['ENGINE']:
            self.stderr.write(self.style.ERROR(
                'DB_ENGINE en .env no apunta a MySQL.\n'
                'Edita .env: DB_ENGINE=django.db.backends.mysql y reconfigura DB_NAME, DB_USER, etc.'
            ))
            sys.exit(1)

        self.stdout.write(f"  Host MySQL : {db_cfg['HOST']}:{db_cfg['PORT']}")
        self.stdout.write(f"  Base datos : {db_cfg['NAME']}")
        self.stdout.write(f"  Usuario    : {db_cfg['USER']}\n")

        # ── Paso 2: Exportar datos desde SQLite ───────────────────────────────
        if not options['skip_dump']:
            self.stdout.write(self.style.WARNING('Paso 1/4 — Exportando datos desde SQLite...'))

            sqlite_path = settings.BASE_DIR / 'db.sqlite3'
            if not sqlite_path.exists():
                self.stderr.write(self.style.ERROR(f'No se encontró db.sqlite3 en {sqlite_path}'))
                sys.exit(1)

            if dry_run:
                self.stdout.write(f'  [DRY RUN] dumpdata → {dump_path}')
            else:
                with open(dump_path, 'w', encoding='utf-8') as f:
                    call_command(
                        'dumpdata',
                        '--natural-foreign',
                        '--natural-primary',
                        '--exclude=contenttypes',
                        '--exclude=auth.permission',
                        '--indent=2',
                        stdout=f,
                    )
                size_kb = dump_path.stat().st_size // 1024
                self.stdout.write(self.style.SUCCESS(f'  Exportados {size_kb} KB → {dump_path}'))
        else:
            if not dump_path.exists():
                self.stderr.write(self.style.ERROR(f'Archivo dump no encontrado: {dump_path}'))
                sys.exit(1)
            self.stdout.write(f'  Usando dump existente: {dump_path}')

        # ── Paso 3: Aplicar migraciones en MySQL ──────────────────────────────
        self.stdout.write(self.style.WARNING('\nPaso 2/4 — Aplicando migraciones en MySQL...'))
        if dry_run:
            self.stdout.write('  [DRY RUN] python manage.py migrate')
        else:
            try:
                call_command('migrate', '--run-syncdb', verbosity=1)
                self.stdout.write(self.style.SUCCESS('  Migraciones aplicadas.'))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'Error en migrate: {exc}'))
                sys.exit(1)

        # ── Paso 4: Cargar datos en MySQL ─────────────────────────────────────
        self.stdout.write(self.style.WARNING('\nPaso 3/4 — Cargando datos en MySQL...'))
        if dry_run:
            self.stdout.write(f'  [DRY RUN] loaddata {dump_path}')
        else:
            try:
                call_command('loaddata', str(dump_path), verbosity=1)
                self.stdout.write(self.style.SUCCESS('  Datos cargados correctamente.'))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'Error en loaddata: {exc}'))
                self.stderr.write(
                    'Sugerencia: verifica que el usuario MySQL tenga permisos suficientes '
                    'y que la BD esté creada con: CREATE DATABASE facci_care CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;'
                )
                sys.exit(1)

        # ── Paso 5: Verificación básica ───────────────────────────────────────
        self.stdout.write(self.style.WARNING('\nPaso 4/4 — Verificando integridad...'))
        if not dry_run:
            try:
                from apps.auth_app.models import CustomUser
                from apps.pacientes.models import Paciente

                usuarios = CustomUser.objects.count()
                pacientes = Paciente.objects.count()
                self.stdout.write(f'  Usuarios  : {usuarios}')
                self.stdout.write(f'  Pacientes : {pacientes}')
                self.stdout.write(self.style.SUCCESS('  Verificación OK.'))
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'Error verificando: {exc}'))

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN completado. Ejecuta sin --dry-run para migrar.'))
        else:
            self.stdout.write(self.style.SUCCESS('=== Migración completada exitosamente ==='))
            self.stdout.write(f'\nEl dump temporal está en: {dump_path}')
            self.stdout.write('Puedes eliminarlo cuando confirmes que todo funciona.')
