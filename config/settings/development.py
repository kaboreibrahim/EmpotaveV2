"""
config/settings/development.py
Base de données locale PostgreSQL — identique à la config en place.
"""
import os

from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']
SECRET_KEY    = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')
# Désactiver HTTPS en dev
CSRF_COOKIE_SECURE    = False
SESSION_COOKIE_SECURE = False

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     'empotage_local',
        'USER':     'postgres',
        'PASSWORD': '1234',
        'HOST':     '127.0.0.1',
        'PORT':     '5432',
    },
}

# Email console en dev par défaut (pas d'envoi réel).
# Pour tester un vrai envoi SMTP en local : USE_REAL_EMAIL=1 avant de lancer runserver.
if os.environ.get('USE_REAL_EMAIL') == '1':
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
