"""
Django settings for config project.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

# Surcharge locale pour le développement (non versionnée) :
# permet de pointer vers une base Postgres locale sans toucher
# aux identifiants de production dans .env
load_dotenv(BASE_DIR / '.env.dev', override=True)

# ---------------------------------------------------------------
# Patch MySQL (conservé au cas où on rebascule sur MySQL)
# ---------------------------------------------------------------
try:
    from django.db.backends.mysql.features import DatabaseFeatures
    DatabaseFeatures.minimum_database_version = None
except ImportError:
    pass

# ---------------------------------------------------------------
# Sécurité de base
# ---------------------------------------------------------------
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',') if origin
]

# ---------------------------------------------------------------
# Auth
# ---------------------------------------------------------------
AUTH_USER_MODEL = 'users.Users'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'apps.users.auth_backends.EmailOrUsernameModelBackend',
]

# ---------------------------------------------------------------
# Apps
# ---------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    # 'django_lifecycle',
    # 'safedelete',
    # Local apps
    'apps.users',
    'apps.audit',
    'apps.referentiels',
    'apps.conteneurs',
    'apps.documents',
    'apps.notification',
    'apps.offline_sync',
    'apps.DashboardAgentSelection',
    'apps.DashboardAgentEmpotage',
    'apps.DashboardClient',
    'apps.DashboardPersonnel',
    'apps.comptabiliteDashboard',
    'apps.error'

]

CRISPY_TEMPLATE_PACK = 'bootstrap4'
CRISPY_CLASS_CONVERTERS = {
    'file': 'form-control-file',
}

# ---------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.CurrentRequestMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'apps/users/templates'),
            os.path.join(BASE_DIR, 'apps/conteneurs/templates'),
            os.path.join(BASE_DIR, 'apps/referentiels/templates'),
            os.path.join(BASE_DIR, 'apps/DashboardAgentSelection/templates'),
            os.path.join(BASE_DIR, 'apps/DashboardAgentEmpotage/templates'),
            os.path.join(BASE_DIR, 'apps/DashboardClient/templates'),
            os.path.join(BASE_DIR, 'apps/DashboardPersonnel/templates'),
            os.path.join(BASE_DIR, 'apps/comptabiliteDashboard/templates'),
            os.path.join(BASE_DIR, 'apps/documents/templates'),
            os.path.join(BASE_DIR, 'apps/notifications/templates'),
            os.path.join(BASE_DIR, 'apps/error/templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.notification.context_processors.notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ---------------------------------------------------------------
# Base de données
# ---------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'empotage_local'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '1234'),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    },
}

# ---------------------------------------------------------------
# Auth Password Validators
# ---------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'apps.users.password_validation.FourDigitPasswordValidator'},
]

# ---------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------
LANGUAGE_CODE = 'fr'
LANGUAGES = [
    ('fr', _('French')),
    ('en', _('English')),
]
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------
# Fichiers statiques et médias
# ---------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = '/medias/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'medias')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------
# Auth URLs
# ---------------------------------------------------------------
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index'
LOGOUT_REDIRECT_URL = 'login'

# ---------------------------------------------------------------
# Email (SMTP)
# ---------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend' if not DEBUG else 'django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# ---------------------------------------------------------------
# Web Push (VAPID / pywebpush) — voir apps/notification/README.md pour la
# génération des clés et la configuration complète.
# ---------------------------------------------------------------
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '')
VAPID_ADMIN_EMAIL = os.environ.get('VAPID_ADMIN_EMAIL', '')

# ---------------------------------------------------------------
# Messages Bootstrap
# ---------------------------------------------------------------
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# ---------------------------------------------------------------
# Sécurité
# ---------------------------------------------------------------
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
APPEND_SLASH = True
