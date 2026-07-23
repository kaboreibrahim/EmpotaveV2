from django.urls import path

from .views.dashboard import DashboardComptableView
from .views.dossier import (
    DossierDetailComptableView, DossierListeComptableView, modifier_paiement, valider_paiement,
)

app_name = 'comptabiliteDashboard'

urlpatterns = [
    path('accueil/', DashboardComptableView.as_view(), name='dashboard-comptabilite'),
    path('dossiers/', DossierListeComptableView.as_view(), name='dossier-liste'),
    path('dossiers/<uuid:pk>/', DossierDetailComptableView.as_view(), name='dossier-detail'),
    path('dossiers/<uuid:dossier_id>/valider-paiement/', valider_paiement, name='dossier-valider-paiement'),
    path('dossiers/<uuid:dossier_id>/modifier-paiement/', modifier_paiement, name='dossier-modifier-paiement'),
]
