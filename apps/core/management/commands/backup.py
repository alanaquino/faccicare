"""
Sistema de backups automatizados para FACCI Care.

Soporta SQLite y MySQL. Comprime BD + archivos media en un .tar.gz con timestamp.

Uso:
  python manage.py backup                    # backup completo
  python manage.py backup --only-db          # solo base de datos
  python manage.py backup --only-media       # solo archivos media
  python manage.py backup --output /ruta/    # directorio destino personalizado
  python manage.py backup --list             # listar backups existentes
  python manage.py backup --cleanup --keep 7 # eliminar backups > 7 días
"""
import gzip
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


def _timestamp():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


class Command(BaseCommand):
    help = 'Crea un backup de la base de datos y archivos media.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default=None,
            help='Directorio donde guardar el backup (default: BASE_DIR/backups/)')
        parser.add_argument('--only-db', action='store_true',
            help='Solo respalda la base de datos')
        parser.add_argument('--only-media', action='store_true',
            help='Solo respalda archivos media')
        parser.add_argument('--list', action='store_true',
            help='Lista los backups existentes en el directorio de backups')
        parser.add_argument('--cleanup', action='store_true',
            help='Elimina backups más antiguos que --keep días')
        parser.add_argument('--keep', type=int, default=30,
            help='Días de retención para --cleanup (default: 30)')

    def handle(self, *args, **options):
        backup_dir = Path(options['output']) if options['output'] else settings.BASE_DIR / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)

        if options['list']:
            self._list_backups(backup_dir)
            return

        if options['cleanup']:
            self._cleanup(backup_dir, options['keep'])
            return

        ts = _timestamp()
        only_db = options['only_db']
        only_media = options['only_media']

        self.stdout.write(self.style.WARNING(f'=== Backup FACCI Care — {ts} ===\n'))

        db_file = media_file = None

        if not only_media:
            db_file = self._backup_database(backup_dir, ts)

        if not only_db:
            media_file = self._backup_media(backup_dir, ts)

        # Empaquetar en .tar.gz único si se respaldaron ambos
        if db_file and media_file:
            bundle = backup_dir / f'facci_backup_{ts}.tar.gz'
            with tarfile.open(bundle, 'w:gz') as tar:
                tar.add(db_file, arcname=db_file.name)
                tar.add(media_file, arcname=media_file.name)
            db_file.unlink()
            media_file.unlink()
            size_mb = bundle.stat().st_size / (1024 * 1024)
            self.stdout.write(self.style.SUCCESS(f'\nBackup completo: {bundle} ({size_mb:.1f} MB)'))
        elif db_file:
            size_mb = db_file.stat().st_size / (1024 * 1024)
            self.stdout.write(self.style.SUCCESS(f'\nBackup BD: {db_file} ({size_mb:.1f} MB)'))
        elif media_file:
            size_mb = media_file.stat().st_size / (1024 * 1024)
            self.stdout.write(self.style.SUCCESS(f'\nBackup media: {media_file} ({size_mb:.1f} MB)'))

    # ── Base de datos ─────────────────────────────────────────────────────────

    def _backup_database(self, backup_dir: Path, ts: str) -> Path:
        db_cfg = settings.DATABASES['default']
        engine = db_cfg['ENGINE']

        self.stdout.write('Respaldando base de datos...')

        if 'sqlite3' in engine:
            return self._backup_sqlite(backup_dir, ts, db_cfg)
        elif 'mysql' in engine:
            return self._backup_mysql(backup_dir, ts, db_cfg)
        else:
            self.stderr.write(self.style.WARNING(f'Motor no soportado para backup nativo: {engine}'))
            return self._backup_dumpdata(backup_dir, ts)

    def _backup_sqlite(self, backup_dir: Path, ts: str, db_cfg: dict) -> Path:
        src = Path(db_cfg['NAME'])
        if not src.exists():
            self.stderr.write(self.style.ERROR(f'SQLite no encontrado: {src}'))
            sys.exit(1)

        dest = backup_dir / f'db_sqlite_{ts}.sqlite3.gz'
        with open(src, 'rb') as f_in, gzip.open(dest, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

        self.stdout.write(self.style.SUCCESS(f'  SQLite → {dest.name}'))
        return dest

    def _backup_mysql(self, backup_dir: Path, ts: str, db_cfg: dict) -> Path:
        dest = backup_dir / f'db_mysql_{ts}.sql.gz'

        cmd = [
            'mysqldump',
            f"--host={db_cfg.get('HOST', 'localhost')}",
            f"--port={db_cfg.get('PORT', '3306')}",
            f"--user={db_cfg['USER']}",
            f"--password={db_cfg['PASSWORD']}",
            '--single-transaction',
            '--quick',
            '--routines',
            '--triggers',
            db_cfg['NAME'],
        ]

        try:
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.decode())

            with gzip.open(dest, 'wb') as f:
                f.write(result.stdout)

            self.stdout.write(self.style.SUCCESS(f'  MySQL dump → {dest.name}'))
            return dest
        except FileNotFoundError:
            self.stderr.write(self.style.WARNING('mysqldump no disponible. Usando dumpdata como fallback.'))
            return self._backup_dumpdata(backup_dir, ts)
        except RuntimeError as exc:
            self.stderr.write(self.style.ERROR(f'Error mysqldump: {exc}'))
            sys.exit(1)

    def _backup_dumpdata(self, backup_dir: Path, ts: str) -> Path:
        dest = backup_dir / f'db_dump_{ts}.json.gz'
        json_tmp = backup_dir / f'_tmp_{ts}.json'

        with open(json_tmp, 'w', encoding='utf-8') as f:
            call_command(
                'dumpdata',
                '--natural-foreign', '--natural-primary',
                '--exclude=contenttypes', '--exclude=auth.permission',
                '--indent=2',
                stdout=f,
            )

        with open(json_tmp, 'rb') as f_in, gzip.open(dest, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        json_tmp.unlink()

        self.stdout.write(self.style.SUCCESS(f'  dumpdata → {dest.name}'))
        return dest

    # ── Media ─────────────────────────────────────────────────────────────────

    def _backup_media(self, backup_dir: Path, ts: str) -> Path:
        media_root = settings.MEDIA_ROOT
        if not Path(media_root).exists():
            self.stdout.write(self.style.WARNING('  Directorio media vacío o no existe. Omitiendo.'))
            return None

        dest = backup_dir / f'media_{ts}.tar.gz'
        with tarfile.open(dest, 'w:gz') as tar:
            tar.add(media_root, arcname='media')

        self.stdout.write(self.style.SUCCESS(f'  Media → {dest.name}'))
        return dest

    # ── Utilidades ────────────────────────────────────────────────────────────

    def _list_backups(self, backup_dir: Path):
        files = sorted(backup_dir.glob('*'), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            self.stdout.write('No hay backups en ' + str(backup_dir))
            return

        self.stdout.write(f'\nBackups en {backup_dir}:\n')
        total = 0
        for f in files:
            size_mb = f.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            self.stdout.write(f'  {mtime}  {size_mb:6.1f} MB  {f.name}')
            total += f.stat().st_size
        self.stdout.write(f'\n  Total: {total / (1024*1024):.1f} MB en {len(files)} archivos')

    def _cleanup(self, backup_dir: Path, keep_days: int):
        cutoff = datetime.now() - timedelta(days=keep_days)
        removed = 0
        freed = 0

        for f in backup_dir.iterdir():
            if f.is_file():
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    freed += f.stat().st_size
                    f.unlink()
                    removed += 1
                    self.stdout.write(f'  Eliminado: {f.name}')

        if removed:
            self.stdout.write(self.style.SUCCESS(
                f'\n{removed} backups eliminados ({freed / (1024*1024):.1f} MB liberados)'
            ))
        else:
            self.stdout.write(f'Sin backups anteriores a {keep_days} días.')
