# Despliegue y actualización en PythonAnywhere

Guía para publicar **FACCI Care** en PythonAnywhere y para actualizarlo cada vez
que haya cambios nuevos en el repositorio.

| Archivo | Para qué sirve |
|---|---|
| `pythonanywhere_update.sh` | Script de actualización: git pull + dependencias + migraciones + estáticos + recarga |
| `pythonanywhere_wsgi.py` | Plantilla del archivo WSGI que pide PythonAnywhere |
| `env.pythonanywhere.example` | Plantilla del `.env` de producción |

En todos los ejemplos, reemplaza `tuusuario` por tu usuario real de PythonAnywhere.

---

## Actualizar (lo que harás normalmente)

Abre una consola **Bash** desde la pestaña *Consoles* del panel y ejecuta:

```bash
cd ~/faccicare
bash deploy/pythonanywhere_update.sh
```

El script hace, en este orden:

1. Activa el entorno virtual y verifica que el repositorio esté limpio.
2. Respalda base de datos + `media/` (`python manage.py backup`) y borra respaldos de más de 7 días.
3. `git fetch` + `git merge --ff-only` de `origin/main`.
4. `pip install -r requirements.txt`.
5. `python manage.py migrate`.
6. `python manage.py collectstatic --clear`.
7. `python manage.py check --deploy`.
8. Recarga la web app con `touch` al archivo WSGI.

Si algún paso falla, el script se detiene ahí y no recarga la aplicación.

### Ajustes sin editar el script

```bash
# Desplegar otra rama
GIT_BRANCH=develop bash deploy/pythonanywhere_update.sh

# Dominio propio (el archivo WSGI se llama distinto)
WSGI_FILE=/var/www/www_faccicare_org_wsgi.py bash deploy/pythonanywhere_update.sh

# Actualización rápida sin respaldo ni reinstalar dependencias
SKIP_BACKUP=1 SKIP_DEPS=1 bash deploy/pythonanywhere_update.sh
```

Variables disponibles: `PA_USER`, `PROJECT_DIR`, `VENV_DIR`, `GIT_REMOTE`,
`GIT_BRANCH`, `WSGI_FILE`, `PA_DOMAIN`, `SKIP_BACKUP`, `SKIP_DEPS`.

### Si el script se detiene por cambios locales

```bash
cd ~/faccicare
git status --short        # ver qué cambió
git checkout -- .         # descartar cambios locales (¡se pierden!)
# o bien:  git stash       # guardarlos para después
```

`.env`, `db.sqlite3`, `media/` y `staticfiles/` están en `.gitignore`, así que el
script nunca los toca.

---

## Instalación inicial (solo la primera vez)

### 1. Clonar el repositorio

```bash
cd ~
git clone https://github.com/alanaquino/faccicare.git faccicare
```

### 2. Crear el entorno virtual

Django 6.0 requiere Python 3.12 o superior; elige la versión más alta que
ofrezca tu cuenta.

```bash
mkvirtualenv --python=/usr/bin/python3.13 faccicare
cd ~/faccicare
pip install -r requirements.txt
```

Eso crea el entorno en `~/.virtualenvs/faccicare`, que es la ruta que el script
de actualización espera por defecto.

### 3. Crear la base de datos MySQL

En la pestaña **Databases** del panel: inicializa MySQL y crea una base llamada
`faccicare` (PythonAnywhere la nombrará `tuusuario$faccicare`). Anota host,
usuario y contraseña.

### 4. Configurar el `.env`

```bash
cp ~/faccicare/deploy/env.pythonanywhere.example ~/faccicare/.env
nano ~/faccicare/.env
```

Genera las dos claves y pégalas en el archivo:

```bash
cd ~/faccicare
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> `FACCI_ENCRYPTION_KEY` se genera **una sola vez**. Si la cambias después, los
> datos sensibles ya cifrados no se podrán descifrar.

### 5. Migrar y crear el usuario administrador

```bash
cd ~/faccicare
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

`seed_data` es solo para desarrollo (exige `DEBUG=True`): no lo ejecutes en
producción.

### 6. Crear la web app

En la pestaña **Web** del panel:

1. *Add a new web app* → **Manual configuration** → la misma versión de Python
   del entorno virtual.
2. **Source code**: `/home/tuusuario/faccicare`
3. **Working directory**: `/home/tuusuario/faccicare`
4. **Virtualenv**: `/home/tuusuario/.virtualenvs/faccicare`
5. **WSGI configuration file**: ábrelo y reemplaza todo su contenido por el de
   `deploy/pythonanywhere_wsgi.py` (ajustando `PROJECT_DIR` si clonaste en otra
   ruta).
6. **Static files**:

   | URL | Directory |
   |---|---|
   | `/static/` | `/home/tuusuario/faccicare/staticfiles` |
   | `/media/`  | `/home/tuusuario/faccicare/media` |

7. **Force HTTPS**: activado (`settings.py` ya aplica `SECURE_SSL_REDIRECT`,
   HSTS y cookies seguras cuando `DEBUG=False`).
8. Pulsa **Reload**.

---

## Verificación y problemas frecuentes

```bash
# Comprobar configuración de producción
cd ~/faccicare && python manage.py check --deploy

# Ver los errores de la aplicación en vivo
tail -f /var/log/tuusuario.pythonanywhere.com.error.log
```

| Síntoma | Causa habitual |
|---|---|
| `DisallowedHost` | Falta el dominio en `DJANGO_ALLOWED_HOSTS` del `.env` |
| CSRF verification failed | Falta `DJANGO_CSRF_TRUSTED_ORIGINS`, o el dominio no coincide con `ALLOWED_HOSTS` |
| La página se ve sin estilos | No corriste `collectstatic`, o el mapeo `/static/` apunta a `static/` en vez de `staticfiles/` |
| Bucle de redirecciones | `DEBUG=False` sin la cabecera `SECURE_PROXY_SSL_HEADER` (ya está en `settings.py`; revisa que uses `config/settings.py` sin modificar) |
| `Access denied for user` en MySQL | Credenciales `DB_*` del `.env` distintas a las de la pestaña *Databases* |
| Los cambios no aparecen | Faltó recargar la web app (el script hace `touch` al WSGI; si falla, usa el botón **Reload**) |
| `NameError`/`ImportError` tras actualizar | Dependencia nueva sin instalar: ejecuta el script sin `SKIP_DEPS=1` |

---

## Respaldos

El script respalda antes de cada actualización, pero también puedes hacerlo a mano:

```bash
cd ~/faccicare
python manage.py backup                     # base de datos + media
python manage.py backup --list              # listar respaldos existentes
python manage.py backup --cleanup --keep 7  # borrar los de más de 7 días
```

Los respaldos se guardan en `~/faccicare/backups/`. Descárgalos de vez en cuando
desde la pestaña *Files*, porque el disco de PythonAnywhere tiene cuota limitada.
