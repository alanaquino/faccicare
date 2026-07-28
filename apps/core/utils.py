"""
FACCI Care — Utilidades globales de apoyo técnico.
"""
import uuid

def generar_codigo_paciente():
    """Genera un código único secuencial o aleatorio para nuevos pacientes."""
    return f"FACCI-{uuid.uuid4().hex[:6].upper()}"

def sanitizar_nombre_archivo(nombre_original):
    """Sanitiza nombres de archivos subidos para evitar problemas de caracteres y paths."""
    import re
    nombre_limpio = re.sub(r'[^a-zA-Z0-9_.-]', '_', nombre_original)
    return nombre_limpio


def get_system_logo_path_or_fallback() -> str:
    from apps.core.models import SistemaConfiguracion
    from django.conf import settings
    from pathlib import Path
    
    config = SistemaConfiguracion.get_solo()
    logo_file = config.logo_reportes or config.logo
    if logo_file:
        try:
            if Path(logo_file.path).exists():
                return logo_file.path
        except ValueError:
            pass
            
    path = Path(settings.BASE_DIR) / "static" / "img" / "Logo-Facci-1.png"
    return str(path) if path.exists() else ""

