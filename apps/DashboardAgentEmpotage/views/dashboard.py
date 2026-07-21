from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from apps.conteneurs.models import Dossier

DASHBOARD_TEMPLATE = 'DashboardAgentEmpotage/pages/dashboard.html'

# Dossiers pour lesquels l'agent d'empotage a encore une action à réaliser.
STATUTS_A_TRAITER = ('empotage_en_cours',)


@login_required
def dashboard_agent_empotage(request):
    """Tableau de bord de l'agent d'empotage : dossiers attribués, avancement, actions à faire."""
    qs = Dossier.objects.select_related('Id_Pays', 'Id_POL', 'Id_POD', 'id_client__user')
    if not request.user.is_superuser:
        qs = qs.filter(Id_Agent_empotage__user=request.user)

    total_dossiers = qs.count()
    total_empotage_en_cours = qs.filter(statut='empotage_en_cours').count()
    total_termines = qs.filter(statut='dossier_termine').count()

    agg = qs.aggregate(nb_iso=Count('isotanks', distinct=True), nb_flexi=Count('flexitanks', distinct=True))
    nb_iso = agg['nb_iso'] or 0
    nb_flexi = agg['nb_flexi'] or 0
    total_conteneurs = nb_iso + nb_flexi

    a_traiter = (
        qs.filter(statut__in=STATUTS_A_TRAITER)
        .order_by('-date_created')[:6]
    )

    recents = qs.order_by('-date_created')[:5]

    return render(request, DASHBOARD_TEMPLATE, {
        'total_dossiers': total_dossiers,
        'total_empotage_en_cours': total_empotage_en_cours,
        'total_termines': total_termines,
        'nb_iso': nb_iso,
        'nb_flexi': nb_flexi,
        'total_conteneurs': total_conteneurs,
        'pct_iso': round(nb_iso / total_conteneurs * 100) if total_conteneurs else 0,
        'pct_flexi': round(nb_flexi / total_conteneurs * 100) if total_conteneurs else 0,
        'a_traiter': a_traiter,
        'recents': recents,
    })
