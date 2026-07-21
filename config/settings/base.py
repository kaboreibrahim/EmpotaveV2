"""
config/settings/base.py
Adapté depuis gestion_conteneurs/settings.py (projet monolithique → multi-apps)
Django 5.0.6 — PostgreSQL — Templates HTML — Auth custom
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / '.env')

# ---------------------------------------------------------------
# Patch MySQL (conservé au cas où on rebascule sur MySQL)
# ---------------------------------------------------------------
try:
    from django.db.backends.mysql.features import DatabaseFeatures
    DatabaseFeatures.minimum_database_version = None
except ImportError:
    pass

ALLOWED_HOSTS = ['*']

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
    'apps.DashboardAgentSelection',
    'apps.DashboardAgentEmpotage',
    'apps.DashboardClient',
    'apps.DashboardPersonnel',
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
STATIC_URL  = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL  = 'medias/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'medias')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------
# Auth URLs (identiques à la prod existante)
# ---------------------------------------------------------------
LOGIN_URL            = 'login'
LOGIN_REDIRECT_URL   = 'index'
LOGOUT_REDIRECT_URL  = 'login'

# ── Email (SMTP cPanel) ──────────────────────────────────────
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = "mail.oils-of-africa.com"
# EMAIL_PORT = 465
# EMAIL_USE_SSL = True
# EMAIL_USE_TLS = False
# EMAIL_HOST_USER = "contact@oils-of-africa.com"
# EMAIL_HOST_PASSWORD = "@AbNnD[G@rSnHFD8"
# DEFAULT_FROM_EMAIL = "contact@oils-of-africa.com"

# Email settings
DEBUG=True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'ibrahimkabore025@gmail.com'  # Replace with your Gmail address
EMAIL_HOST_PASSWORD = 'hrwc jlvv ksqy gfeq'

# ---------------------------------------------------------------
# Messages Bootstrap
# ---------------------------------------------------------------
MESSAGE_TAGS = {
    messages.DEBUG:   'alert-secondary',
    messages.INFO:    'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR:   'alert-danger',
}

# ---------------------------------------------------------------
# Sécurité
# ---------------------------------------------------------------
CSRF_COOKIE_SECURE  = True
SESSION_COOKIE_SECURE = True
APPEND_SLASH = True

