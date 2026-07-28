"""
Cifrado de campos sensibles en reposo para FACCI Care.

Usa Fernet (AES-128-CBC + HMAC-SHA256). Los valores cifrados llevan el
prefijo 'enc:' para distinguirlos de datos legacy sin cifrar.

Si FACCI_ENCRYPTION_KEY no está configurado (dev), los campos pasan el
valor sin modificar — el sistema sigue funcionando sin cifrado.

Generación de clave:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import base64

from django.conf import settings
from django.db import models

_SENTINEL = 'enc:'


def _get_fernet():
    key = getattr(settings, 'FACCI_ENCRYPTION_KEY', '') or ''
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode())
    except Exception:
        return None


def encrypt(value: str) -> str:
    """Cifra un string. Devuelve el valor original si no hay clave configurada."""
    if not value:
        return value
    if value.startswith(_SENTINEL):
        return value  # ya cifrado
    f = _get_fernet()
    if f is None:
        return value
    return _SENTINEL + f.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    """Descifra un string. Devuelve el valor original si no tiene el prefijo 'enc:'."""
    if not value:
        return value
    if not value.startswith(_SENTINEL):
        return value  # texto plano legacy — sin clave o dato antiguo
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value[len(_SENTINEL):].encode()).decode()
    except Exception:
        return value  # fallback si la clave cambió


# ── Campos Django personalizados ──────────────────────────────────────────────

class EncryptedCharField(models.CharField):
    """CharField que cifra automáticamente en escritura y descifra en lectura.

    Usa max_length=512 para acomodar la salida de Fernet en base64.
    No usar con unique=True ni como campo de búsqueda en ORM — usar un
    campo de hash separado para esos casos.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 512)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value else value

    def to_python(self, value):
        return decrypt(value) if value else value

    def get_prep_value(self, value):
        return encrypt(value) if value else value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs


class EncryptedTextField(models.TextField):
    """TextField que cifra automáticamente en escritura y descifra en lectura."""

    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value else value

    def to_python(self, value):
        return decrypt(value) if value else value

    def get_prep_value(self, value):
        return encrypt(value) if value else value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, args, kwargs
