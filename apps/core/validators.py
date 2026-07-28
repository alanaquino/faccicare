"""
FACCI Care — Validadores globales de formatos clínicos y personales.
"""
from django.core.exceptions import ValidationError
import re

def validar_cedula(value):
    """Valida el formato de la Cédula de Identidad de República Dominicana (XXX-XXXXXXX-X)."""
    cedula_regex = r'^\d{3}-\d{7}-\d{1}$'
    if not re.match(cedula_regex, value):
        raise ValidationError("La cédula debe cumplir con el formato oficial: 001-0000000-0.")

def validar_telefono(value):
    """Valida números telefónicos de RD (809/829/849)."""
    tel_regex = r'^(809|829|849)-\d{3}-\d{4}$'
    if not re.match(tel_regex, value):
        raise ValidationError("El teléfono debe cumplir con el formato: 809-555-5555.")
