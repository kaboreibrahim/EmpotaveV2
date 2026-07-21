from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import render

from apps.conteneurs.models import Dossier
from apps.documents.models import Document

DASHBOARD_TEMPLATE = 'DashboardClient/accueil.html'

# Statuts documentaires pour lesquels le client n'a rien de plus à faire que
# d'attendre (déposé mais pas encore validé par le personnel).
STATUTS_DOCUMENT_EN_ATTENTE = ('ajoute', 'en_attente_validation')

# Dossiers pour lesquels une action ou un suivi est encore attendu côté client.
STATUTS_EN_COURS = ('en_attente', 'selection_en_cours', 'empotage_en_cours')


@login_required
def dashboard_client(request):
    """Tableau de bord du client : ses dossiers, leur avancement et ses documents en attente."""
    if not hasattr(request.user, 'client'):
        raise PermissionDenied("Cet espace est réservé aux clients.")

    qs = Dossier.objects.select_related('Id_Pays', 'Id_POL', 'Id_POD').filter(id_client__user=request.user)

    total_dossiers = qs.count()
    total_en_attente = qs.filter(statut='en_attente').count()
    total_en_cours = qs.filter(statut__in=('selection_en_cours', 'empotage_en_cours')).count()
    total_termines = qs.filter(statut='dossier_termine').count()

    agg = qs.aggregate(nb_iso=Count('isotanks', distinct=True), nb_flexi=Count('flexitanks', distinct=True))
    nb_iso = agg['nb_iso'] or 0
    nb_flexi = agg['nb_flexi'] or 0
    total_conteneurs = nb_iso + nb_flexi

    en_cours = qs.filter(statut__in=STATUTS_EN_COURS).order_by('-date_created')[:6]
    recents = qs.order_by('-date_created')[:5]

    documents_qs = Document.objects.select_related('dossier', 'type_document').filter(dossier__id_client__user=request.user)
    documents_recents = documents_qs.order_by('-date_created')[:5]
    total_documents_en_attente = documents_qs.filter(statut__in=STATUTS_DOCUMENT_EN_ATTENTE).count()

    return render(request, DASHBOARD_TEMPLATE, {
        'total_dossiers': total_dossiers,
        'total_en_attente': total_en_attente,
        'total_en_cours': total_en_cours,
        'total_termines': total_termines,
        'nb_iso': nb_iso,
        'nb_flexi': nb_flexi,
        'total_conteneurs': total_conteneurs,
        'en_cours': en_cours,
        'recents': recents,
        'documents_recents': documents_recents,
        'total_documents_en_attente': total_documents_en_attente,
    })
