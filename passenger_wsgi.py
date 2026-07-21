import os
import sys

# Chemin vers l'environnement virtuel
VENV_PATH = os.path.expanduser('~/empotage-oils-of-africa-v3/venv')
PYTHON_PATH = os.path.join(VENV_PATH, 'bin', 'python3')

# Ajouter le chemin de l'application
sys.path.insert(0, os.path.expanduser('~/empotage-oils-of-africa-v3'))

# Configurer les variables d'environnement
os.environ['PYTHON_EGG_CACHE'] = os.path.expanduser('~/empotage-oils-of-africa-v3/.python-egg')
os.environ['DJANGO_SETTINGS_MODULE'] = 'gestion_conteneurs.settings'

# Importer l'application WSGI
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()