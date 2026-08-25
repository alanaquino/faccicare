"""
FACCI Care — Archivo WSGI para PythonAnywhere.

Copia el contenido de este archivo en el WSGI configuration file que
PythonAnywhere crea para tu web app, normalmente:

    /var/www/<tu_usuario>_pythonanywhere_com_wsgi.py

Se edita desde la pestana "Web" del panel -> "WSGI configuration file".
Reemplaza <tu_usuario> por tu usuario real de PythonAnywhere.

Nota: PythonAnywhere NO ejecuta este archivo desde el repositorio; hay que
pegar su contenido en la ruta /var/www/... indicada arriba.
"""
import os
import sys

# ── 1. Ruta del proyecto ──────────────────────────────────────────────────────
PROJECT_DIR = os.path.expanduser('~/faccicare')
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# ── 2. Variables de entorno desde el .env del proyecto ────────────────────────
# python-decouple lee el .env del directorio de trabajo, que en PythonAnywhere
# no es el del proyecto. Cargarlo aqui garantiza que settings.py vea el .env.
_env_path = os.path.join(PROJECT_DIR, '.env')
if os.path.exists(_env_path):
    with open(_env_path, encoding='utf-8') as _env_file:
        for _line in _env_file:
            _line = _line.strip()
            if not _line or _line.startswith('#') or '=' not in _line:
                continue
            _key, _value = _line.split('=', 1)
            os.environ.setdefault(_key.strip(), _value.strip().strip('"').strip("'"))

# ── 3. Aplicacion Django ──────────────────────────────────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
