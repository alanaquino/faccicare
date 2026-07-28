"""
FACCI Care — Helpers de formato y presentación visual.
"""

def formatear_tamano_archivo(bytes_size):
    """Convierte bytes a un string legible (KB, MB, GB)."""
    factor = 1024
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < factor:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= factor
    return f"{bytes_size:.1f} TB"

def calcular_edad(fecha_nacimiento):
    """Calcula la edad exacta del paciente infantil en años y meses."""
    from datetime import date
    if not fecha_nacimiento:
        return "N/D"
    today = date.today()
    age_years = today.year - fecha_nacimiento.year - ((today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    return f"{age_years} años"
