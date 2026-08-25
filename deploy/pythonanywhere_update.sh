#!/usr/bin/env bash
#
# FACCI Care — Actualizacion del despliegue en PythonAnywhere
# =============================================================================
# Ejecuta este script desde una consola Bash de PythonAnywhere:
#
#   cd ~/faccicare_new
#   bash deploy/pythonanywhere_update.sh
#
# Que hace, en orden:
#   1. Verifica que no haya cambios locales sin guardar.
#   2. Respalda la base de datos y los archivos media.
#   3. Trae los ultimos cambios de la rama configurada.
#   4. Instala/actualiza dependencias.
#   5. Aplica migraciones.
#   6. Recolecta archivos estaticos.
#   7. Ejecuta un chequeo de despliegue (--deploy).
#   8. Recarga la aplicacion web (touch al archivo WSGI).
#
# Variables que puedes ajustar sin editar el script:
#   PA_USER        Usuario de PythonAnywhere        (default: $USER)
#   PROJECT_DIR    Ruta del proyecto                (default: ~/faccicare_new)
#   VENV_DIR       Ruta del entorno virtual         (default: ~/.virtualenvs/facci-care)
#   GIT_REMOTE     Remoto de git                    (default: origin)
#   GIT_BRANCH     Rama a desplegar                 (default: main)
#   WSGI_FILE      Archivo WSGI de la web app       (default: /var/www/${PA_USER}_pythonanywhere_com_wsgi.py)
#   SKIP_BACKUP=1  Omite el respaldo previo
#   SKIP_DEPS=1    Omite `pip install -r requirements.txt`
#
# Ejemplo con dominio propio:
#   WSGI_FILE=/var/www/www_faccicare_org_wsgi.py bash deploy/pythonanywhere_update.sh
# =============================================================================

set -euo pipefail

# ── Auto-copia fuera del repositorio ──────────────────────────────────────────
# Bash lee el script por partes mientras lo ejecuta. Como mas abajo hacemos
# `git checkout`/`git merge` sobre el mismo repositorio donde vive este archivo,
# el contenido bajo el cursor de lectura puede cambiar a mitad de ejecucion.
# Para evitarlo, nos copiamos a un temporal y seguimos desde ahi.
if [ -z "${FACCI_UPDATE_REEXEC:-}" ]; then
    _self_copy="${TMPDIR:-/tmp}/faccicare_update_$$.sh"
    cp "$0" "$_self_copy"
    FACCI_UPDATE_REEXEC=1 exec bash "$_self_copy"
fi
trap 'rm -f "$0"' EXIT

PA_USER="${PA_USER:-${USER:-$(whoami)}}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/faccicare_new}"
VENV_DIR="${VENV_DIR:-$HOME/.virtualenvs/facci-care}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
GIT_BRANCH="${GIT_BRANCH:-main}"
WSGI_FILE="${WSGI_FILE:-/var/www/${PA_USER}_pythonanywhere_com_wsgi.py}"

log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[0;32m    OK: %s\033[0m\n' "$*"; }
warn() { printf '\033[0;33m    AVISO: %s\033[0m\n' "$*"; }
die()  { printf '\n\033[0;31m!! ERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ── 0. Preparacion ────────────────────────────────────────────────────────────
[ -d "$PROJECT_DIR" ] || die "No existe el proyecto en $PROJECT_DIR (ajusta PROJECT_DIR)."
cd "$PROJECT_DIR"
[ -f manage.py ] || die "$PROJECT_DIR no parece el proyecto Django (falta manage.py)."

log "Activando entorno virtual: $VENV_DIR"
[ -f "$VENV_DIR/bin/activate" ] || die "No hay entorno virtual en $VENV_DIR (ajusta VENV_DIR)."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
ok "$(python --version) — $(python -c 'import sys; print(sys.prefix)')"

if [ ! -f .env ]; then
    warn "No se encontro .env en $PROJECT_DIR; se usaran los valores por defecto de settings.py."
fi

# ── 1. Cambios locales sin guardar ────────────────────────────────────────────
log "Revisando el estado del repositorio"
if [ -n "$(git status --porcelain)" ]; then
    git status --short
    die "Hay cambios locales sin guardar. Haz commit/stash (o descartalos) y vuelve a ejecutar."
fi
ok "Arbol de trabajo limpio."

# ── 2. Respaldo previo ────────────────────────────────────────────────────────
if [ "${SKIP_BACKUP:-0}" = "1" ]; then
    warn "Respaldo omitido (SKIP_BACKUP=1)."
else
    log "Respaldando base de datos y archivos media"
    python manage.py backup || die "Fallo el respaldo. Se aborta la actualizacion."
    # Conserva solo los ultimos 7 dias para no llenar la cuota de disco.
    python manage.py backup --cleanup --keep 7 || warn "No se pudo limpiar respaldos antiguos."
fi

# ── 3. Traer los ultimos cambios ──────────────────────────────────────────────
log "Descargando cambios de $GIT_REMOTE/$GIT_BRANCH"
git fetch "$GIT_REMOTE" "$GIT_BRANCH"
COMMIT_ANTES="$(git rev-parse HEAD)"
git checkout "$GIT_BRANCH"
git merge --ff-only "$GIT_REMOTE/$GIT_BRANCH" \
    || die "No se pudo avanzar en modo fast-forward. Revisa la rama local $GIT_BRANCH."
COMMIT_DESPUES="$(git rev-parse HEAD)"

if [ "$COMMIT_ANTES" = "$COMMIT_DESPUES" ]; then
    ok "Ya estaba al dia en $(git rev-parse --short HEAD)."
else
    ok "Actualizado: $(git rev-parse --short "$COMMIT_ANTES") -> $(git rev-parse --short HEAD)"
    git --no-pager log --oneline "$COMMIT_ANTES..$COMMIT_DESPUES" | sed 's/^/       /'
fi

# ── 4. Dependencias ───────────────────────────────────────────────────────────
if [ "${SKIP_DEPS:-0}" = "1" ]; then
    warn "Instalacion de dependencias omitida (SKIP_DEPS=1)."
else
    log "Instalando dependencias de requirements.txt"
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --upgrade
    ok "Dependencias al dia."
fi

# ── 5. Migraciones ────────────────────────────────────────────────────────────
log "Migraciones pendientes"
python manage.py showmigrations --plan | grep -v '^\[X\]' || true
python manage.py migrate --noinput
ok "Migraciones aplicadas."

# ── 6. Archivos estaticos ─────────────────────────────────────────────────────
log "Recolectando archivos estaticos"
python manage.py collectstatic --noinput --clear
ok "Estaticos recolectados en $PROJECT_DIR/staticfiles"

# ── 7. Chequeo de despliegue ──────────────────────────────────────────────────
log "Chequeo de configuracion para produccion"
python manage.py check --deploy || warn "El chequeo reporto advertencias; revisa la salida de arriba."

# ── 8. Recargar la aplicacion web ─────────────────────────────────────────────
log "Recargando la aplicacion web"
if [ -f "$WSGI_FILE" ]; then
    touch "$WSGI_FILE"
    ok "Recargada mediante touch $WSGI_FILE"
elif command -v pa >/dev/null 2>&1; then
    pa website reload --domain "${PA_DOMAIN:-${PA_USER}.pythonanywhere.com}" \
        && ok "Recargada con el CLI 'pa'."
else
    warn "No se encontro $WSGI_FILE ni el CLI 'pa'."
    warn "Recarga manualmente desde la pestana 'Web' del panel de PythonAnywhere."
fi

log "Actualizacion completada — commit $(git rev-parse --short HEAD)"
