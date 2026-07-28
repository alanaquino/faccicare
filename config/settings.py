"""
FACCI Care — Configuración Django
Sistema de detección temprana de cáncer pediátrico — República Dominicana.
"""
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('DJANGO_SECRET_KEY', default='django-insecure-faccicare-dev-key-solo-para-desarrollo')
DEBUG = config('DJANGO_DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    # Apps FACCI Care
    'apps.core',
    'apps.auth_app',
    'apps.dashboard',
    'apps.pacientes',
    'apps.cribado',
    'apps.referencias',
    'apps.seguimiento',
    'apps.padres',
    'apps.documentos',
    'apps.reportes',
    'apps.usuarios',
    'apps.notificaciones',
    'apps.casos',  # kept for migration history
    'apps.laboratorio',
    'apps.psicosocial',
    'apps.alojamiento',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.middleware.LoginRequiredMiddleware',
    'apps.core.middleware.ControlAccesoPorRolMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.notificaciones.context_processors.unread_notifications',
                'apps.core.context_processors.sistema_configuracion',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ── Base de datos ─────────────────────────────────────────────────────────────
_DB_ENGINE = config('DB_ENGINE', default='django.db.backends.sqlite3')

DATABASES = {
    'default': {
        'ENGINE': _DB_ENGINE,
        'NAME': config('DB_NAME', default='') or str(BASE_DIR / 'db.sqlite3'),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='3306'),
    }
}

if _DB_ENGINE == 'django.db.backends.mysql':
    DATABASES['default']['OPTIONS'] = {
        'charset': 'utf8mb4',
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
    }

AUTH_USER_MODEL = 'auth_app.CustomUser'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Argon2 como algoritmo principal de hash de contraseñas (con salt).
# PBKDF2 se mantiene como respaldo para verificar contraseñas antiguas;
# Django las re-cifra a Argon2 automáticamente en el siguiente login.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]

# ── Internacionalización ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Santo_Domingo'
USE_I18N = True
USE_TZ = True

# ── Archivos estáticos ────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Autenticación ─────────────────────────────────────────────────────────────
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@faccicare.org')

# ── Cifrado de datos sensibles ────────────────────────────────────────────────
# Genera clave con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FACCI_ENCRYPTION_KEY = config('FACCI_ENCRYPTION_KEY', default='')

# Clickjacking: SAMEORIGIN (no DENY) para poder previsualizar documentos del
# propio sitio (PDF/imágenes) dentro de un <iframe> del mismo origen, como el
# visor del expediente del paciente. Sigue bloqueando el framing desde sitios
# externos. Aplica también en desarrollo, donde Django sirve /media/ y el
# XFrameOptionsMiddleware añade el header a esas respuestas.
X_FRAME_OPTIONS = 'SAMEORIGIN'

# ── Seguridad (producción) ────────────────────────────────────────────────────
# Orígenes de confianza para CSRF. Por defecto se derivan de ALLOWED_HOSTS con
# https:// (necesario detrás de un proxy TLS como PythonAnywhere o Nginx).
CSRF_TRUSTED_ORIGINS = config(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    default=','.join(
        f'https://{host}' for host in ALLOWED_HOSTS
        if host not in ('*', 'localhost', '127.0.0.1')
    ),
    cast=Csv(),
)

if not DEBUG:
    # El TLS lo termina el proxy y la petición llega por HTTP; sin esta cabecera
    # SECURE_SSL_REDIRECT provoca un bucle infinito de redirecciones.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    # Rate limiting: protege la API contra abuso y fuerza bruta.
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/min',
        'user': '200/min',
    },
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'facci': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'facci',
        },
    },
    'loggers': {
        'facci.acceso': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
