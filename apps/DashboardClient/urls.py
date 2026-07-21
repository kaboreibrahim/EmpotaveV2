from django.urls import path

from .views.conteneur import ConteneurDetailView
from .views.dashboard import dashboard_client
from .views.document import DocumentListeView
from .views.dossier.detail import DossierDetailView
from .views.dossier.liste import DossierListeView

app_name = 'DashboardClient'

urlpatterns = [
    path('accueil/', dashboard_client, name='dashboard-client'),
    path('dossiers/', DossierListeView.as_view(), name='dossier-liste'),
    path('dossiers/<uuid:pk>/', DossierDetailView.as_view(), name='dossier-detail'),
    path('conteneurs/<uuid:pk>/', ConteneurDetailView.as_view(), name='conteneur-detail'),
    path('documents/', DocumentListeView.as_view(), name='document-liste'),
]
