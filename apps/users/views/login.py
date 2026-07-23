import logging
import re

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.shortcuts import redirect, render

logger = logging.getLogger(__name__)

User = get_user_model()

CODE_RE = re.compile(r'^\d{4}$')

ROLE_REDIRECTS = {
    'agent_selection': 'DashboardAgentSelection:dashboard-agent-selection',
    'agent_empotage':  'DashboardAgentEmpotage:dashboard-agent-empotage',
    'client':          'DashboardClient:dashboard-client',
    'personnel':       'DashboardPersonnel:dashboard-personnel',
    'comptable':       'comptabiliteDashboard:dashboard-comptabilite',
}

ROLE_LABELS = {
    'agent_selection': 'Agent de sélection',
    'agent_empotage':  "Agent d'empotage",
    'client':          'Client',
    'personnel':       'Personnel',
    'comptable':       'Comptable',
}


def _welcome_message(user):
    nom_complet = user.get_full_name() or user.username
    return f"Bienvenue, {nom_complet} ! Vous êtes connecté ."


def _welcome_redirect(request):
    url_name = ROLE_REDIRECTS.get(request.user.user_type)
    if url_name:
        return redirect(url_name)
    return redirect('users:login')


def login_view(request):
    if request.method == 'POST':
        identifiant = request.POST.get('email', '').strip()
        code = request.POST.get('password', '')

        if not CODE_RE.match(code):
            messages.error(request, 'Le code doit contenir exactement 4 chiffres.')
            return render(request, 'users/login.html')

        user = authenticate(request, username=identifiant, password=code)
        if user is not None:
            login(request, user)
            messages.success(request, _welcome_message(user))
            return _welcome_redirect(request)

        messages.error(request, 'Identifiant ou code incorrect.')

    return render(request, 'users/login.html')
