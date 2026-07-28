"""
Cifra en reposo los datos sensibles existentes en la BD.

Ejecutar una sola vez al activar FACCI_ENCRYPTION_KEY en producción.
Los valores ya cifrados (prefijo 'enc:') son omitidos automáticamente.

Uso:
  python manage.py encrypt_sensitive_data           # cifra todo
  python manage.py encrypt_sensitive_data --dry-run # solo muestra qué cifrará
"""
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.core.encryption import encrypt, decrypt, _SENTINEL


class Command(BaseCommand):
    help = 'Cifra campos sensibles existentes en la base de datos.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
            help='Muestra cuántos registros serían cifrados sin modificar la BD')

    def handle(self, *args, **options):
        if not getattr(settings, 'FACCI_ENCRYPTION_KEY', ''):
            self.stderr.write(self.style.ERROR(
                'FACCI_ENCRYPTION_KEY no está configurado en .env. '
                'Genera una clave con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            ))
            return

        dry_run = options['dry_run']
        self.stdout.write(self.style.WARNING('=== Cifrado de datos sensibles ===\n'))
        if dry_run:
            self.stdout.write('  [DRY RUN] — no se modificará la BD\n')

        total = 0
        total += self._cifrar_usuarios(dry_run)
        total += self._cifrar_pacientes(dry_run)
        total += self._cifrar_padres(dry_run)

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(f'{total} campos serían cifrados. Ejecuta sin --dry-run para aplicar.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'{total} campos cifrados correctamente.'))

    def _needs_encryption(self, value: str) -> bool:
        return bool(value) and not value.startswith(_SENTINEL)

    def _cifrar_usuarios(self, dry_run: bool) -> int:
        from apps.auth_app.models import CustomUser
        count = 0
        qs = CustomUser.objects.exclude(telefono='').exclude(telefono__isnull=True)
        for user in qs:
            if self._needs_encryption(user.telefono):
                count += 1
                if not dry_run:
                    # Escribir directamente al campo para que pase por get_prep_value
                    CustomUser.objects.filter(pk=user.pk).update(
                        telefono=encrypt(user.telefono)
                    )
        self.stdout.write(f'  Usuarios   (telefono)          : {count} registros {"por cifrar" if dry_run else "cifrados"}')
        return count

    def _cifrar_pacientes(self, dry_run: bool) -> int:
        from apps.pacientes.models import Paciente
        count = 0
        for p in Paciente.objects.all():
            update = {}
            for field in ('direccion', 'alergias', 'antecedentes_medicos'):
                val = getattr(p, field, '')
                if self._needs_encryption(val):
                    count += 1
                    update[field] = encrypt(val)
            if update and not dry_run:
                Paciente.objects.filter(pk=p.pk).update(**update)
        self.stdout.write(f'  Pacientes  (dir/alerg/antec)   : {count} campos {"por cifrar" if dry_run else "cifrados"}')
        return count

    def _cifrar_padres(self, dry_run: bool) -> int:
        from apps.padres.models import PadreTutor
        count = 0
        for pt in PadreTutor.objects.all():
            update = {}
            for field in ('direccion', 'contacto_emergencia', 'telefono_emergencia'):
                val = getattr(pt, field, '')
                if self._needs_encryption(val):
                    count += 1
                    update[field] = encrypt(val)
            if update and not dry_run:
                PadreTutor.objects.filter(pk=pt.pk).update(**update)
        self.stdout.write(f'  Padres/Tut (dir/contacto/tel)  : {count} campos {"por cifrar" if dry_run else "cifrados"}')
        return count
