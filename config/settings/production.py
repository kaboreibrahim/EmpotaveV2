"""
config/settings/production.py
Serveur de production — c2453269c (MySQL ou PostgreSQL selon env).
Les credentials sont lus depuis les variables d'environnement.
"""
import os
from .base import *

DEBUG  = True
SECRET_KEY    = os.environ['DJANGO_SECRET_KEY']
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'empotage-oils-of-africa.net,www.empotage-oils-of-africa.net,gestion.empotage-oils-of-africa.net').split(',')

# PostgreSQL prod
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

CSRF_COOKIE_SECURE    = True
SESSION_COOKIE_SECURE = True

# CSRF pour les domaines prod
CSRF_TRUSTED_ORIGINS = [
    'https://empotage-oils-of-africa.net',
    'https://www.empotage-oils-of-africa.net',
    'https://gestion.empotage-oils-of-africa.net',
]
