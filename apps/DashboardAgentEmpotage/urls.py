
from django.urls import path
from .views.dashboard import dashboard_agent_empotage
from .views.dossier_empotage.liste import DossierListeView, DossierListeTerminerView
from .views.dossier_empotage.detail import DossierDetailView
from .views.dossier_empotage.create import renseigner_empotage
from .views.conteneur.detail import ConteneurDetailView
from .views.rapport import generate_dossier_report, soumettre_dossier

app_name = 'DashboardAgentEmpotage'

urlpatterns = [
    path('accueil/', dashboard_agent_empotage, name='dashboard-agent-empotage'),
    path('dossiers/', DossierListeView.as_view(), name='dossier-liste'),
    path('dossiers/termines/', DossierListeTerminerView.as_view(), name='dossier-liste-terminer'),
    path('dossiers/<uuid:dossier_id>/', DossierDetailView.as_view(), name='dossier-detail'),
    path('conteneurs/<uuid:pk>/empoter/', renseigner_empotage, name='conteneur-empoter'),
    path('conteneurs/<uuid:pk>/', ConteneurDetailView.as_view(), name='conteneur-detail'),
    path('dossiers/<uuid:dossier_id>/rapport/', generate_dossier_report, name='dossier-rapport'),
    path('dossiers/<uuid:dossier_id>/soumettre/', soumettre_dossier, name='dossier-soumettre'),
]
