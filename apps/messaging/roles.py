"""
apps/messaging/roles.py
La messagerie est accessible depuis les 5 tableaux de bord (un par role),
chacun avec son propre namespace d'URLs et son propre template de base. Ce
module fait le lien entre `user.user_type` et : vers quel tableau de bord /
quelle liste de dossiers revenir, et surtout quel template de base
(sidebar, topbar, notifications...) les pages de messagerie doivent etendre
— pas de coquille separee, la messagerie s'affiche dans le meme habillage
que le reste du tableau de bord de l'utilisateur.
"""
from apps.users.views.login import ROLE_REDIRECTS

ROLE_DOSSIERS_URL = {
    'agent_selection': 'DashboardAgentSelection:dossier-liste',
    'agent_empotage':  'DashboardAgentEmpotage:dossier-liste',
    'client':          'DashboardClient:dossier-liste',
    'personnel':       'DashboardPersonnel:dossier-liste',
    'comptable':       'comptabiliteDashboard:dossier-liste',
}

ROLE_BASE_TEMPLATE = {
    'agent_selection': 'DashboardAgentSelection/base_agent_selection.html',
    'agent_empotage':  'DashboardAgentEmpotage/base_agent_empotage.html',
    'client':          'DashboardClient/base_client.html',
    'personnel':       'DashboardPersonnel/base_personnel.html',
    'comptable':       'comptabiliteDashboard/base_comptabilite.html',
}

# Repli si un role n'a pas (encore) de tableau de bord dedie.
BASE_TEMPLATE_PAR_DEFAUT = 'DashboardPersonnel/base_personnel.html'


def dashboard_url_name(user_type):
    return ROLE_REDIRECTS.get(user_type)


def dossiers_url_name(user_type):
    return ROLE_DOSSIERS_URL.get(user_type)


def base_template_name(user_type):
    return ROLE_BASE_TEMPLATE.get(user_type, BASE_TEMPLATE_PAR_DEFAUT)
