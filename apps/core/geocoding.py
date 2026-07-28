from django.utils import timezone


NOMINATIM_SEARCH_URL = 'https://nominatim.openstreetmap.org/search'
NOMINATIM_USER_AGENT = 'FACCI-Care-Django/1.0'
PAIS_GEOCODIFICACION = 'Republica Dominicana'


def normalizar_direccion_centro(centro):
    partes = [
        getattr(centro, 'nombre', ''),
        getattr(centro, 'direccion', ''),
        getattr(centro, 'municipio', ''),
        getattr(centro, 'provincia', ''),
        PAIS_GEOCODIFICACION,
    ]
    partes_limpias = []
    for parte in partes:
        valor = ' '.join(str(parte or '').split())
        if valor and valor not in partes_limpias:
            partes_limpias.append(valor)
    return ', '.join(partes_limpias)


def obtener_coordenadas_centro(centro, timeout=5):
    consulta = normalizar_direccion_centro(centro)
    if not consulta:
        return None, None

    try:
        import requests
    except ImportError:
        return None, None

    try:
        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params={
                'format': 'json',
                'q': consulta,
                'limit': 1,
                'countrycodes': 'do',
            },
            headers={
                'User-Agent': NOMINATIM_USER_AGENT,
                'Accept-Language': 'es',
            },
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError, TypeError):
        return None, None

    if not isinstance(data, list) or not data:
        return None, None

    try:
        latitud = round(float(data[0].get('lat')), 6)
        longitud = round(float(data[0].get('lon')), 6)
    except (TypeError, ValueError):
        return None, None

    return latitud, longitud


def aplicar_geocodificacion_centro(centro):
    consulta = normalizar_direccion_centro(centro)
    centro.direccion_normalizada = consulta or None

    latitud, longitud = obtener_coordenadas_centro(centro)
    if latitud is None or longitud is None:
        return False

    centro.latitud = latitud
    centro.longitud = longitud
    centro.coordenadas_actualizadas = timezone.now()
    return True


def guardar_geocodificacion_centro(centro):
    coordenadas_actualizadas = aplicar_geocodificacion_centro(centro)
    update_fields = ['direccion_normalizada']
    if coordenadas_actualizadas:
        update_fields += ['latitud', 'longitud', 'coordenadas_actualizadas']

    centro._skip_geocoding = True
    try:
        centro.save(update_fields=update_fields)
    finally:
        centro._skip_geocoding = False

    return coordenadas_actualizadas
