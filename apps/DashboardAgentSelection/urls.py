
from django.urls import path
from .views.dashboard import dashboard_agent_selection
from .views.dossier_selection.list import DossierListeView, DossierListeTerminerView
from .views.dossier_selection.detail import DossierDetailView
from .views.dossier_selection.create import ajouter_conteneur, modifier_conteneur
from .views.conteneur.detail import ConteneurDetailView
from .views.rapport import generate_dossier_report, soumettre_dossier

app_name = 'DashboardAgentSelection'

urlpatterns = [
    path('accueil/', dashboard_agent_selection, name='dashboard-agent-selection'),
    path('dossiers/', DossierListeView.as_view(), name='dossier-liste'),
    path('dossiers/termines/', DossierListeTerminerView.as_view(), name='dossier-liste-terminer'),
    path('dossiers/<uuid:dossier_id>/', DossierDetailView.as_view(), name='dossier-detail'),
    path('dossiers/<uuid:dossier_id>/conteneurs/ajouter/', ajouter_conteneur, name='conteneur-create'),
    path('conteneurs/<uuid:pk>/', ConteneurDetailView.as_view(), name='conteneur-detail'),
    path('conteneurs/<uuid:pk>/modifier/', modifier_conteneur, name='conteneur-update'),
    path('dossiers/<uuid:dossier_id>/rapport/', generate_dossier_report, name='dossier-rapport'),
    path('dossiers/<uuid:dossier_id>/soumettre/', soumettre_dossier, name='dossier-soumettre'),
]
