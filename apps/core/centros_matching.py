"""Emparejamiento de texto libre con registros CentroSalud.

Módulo sin dependencias de Django (recibe el modelo por argumento) para poder
importarse con seguridad desde migraciones de datos y desde pruebas.
"""


def match_centro_por_nombre(CentroSaludModel, nombre):
    """Retorna el CentroSalud cuyo nombre coincide (case-insensitive) con `nombre`.

    Retorna None si `nombre` es vacío/None o no hay coincidencia.
    """
    if not nombre:
        return None
    nombre = nombre.strip()
    if not nombre:
        return None
    return CentroSaludModel.objects.filter(nombre__iexact=nombre).first()
