from django.urls import path
from .views.accueil import DashboardPersonnel
from .views.referentiels.pays import CreatePays, ListePays, ModifierPays
from .views.referentiels.commodite import CreerCommodite, DeleteCommodite, ListeCommodites, ModifierCommodite
from .views.referentiels.pol import CreerPOL, DeletePOL, ListePOL, ModifierPOL
from .views.referentiels.pod import CreerPOD, DeletePOD, ListePOD, ModifierPOD
from .views.referentiels.compagnie import CreerCompagnieMaritime, DeleteCompagnieMaritime, ListeCompagnieMaritime, ModifierCompagnieMaritime
from .views.referentiels.site_selection import CreerSiteSelection, DeleteSiteSelection, ListeSiteSelection, ModifierSiteSelection
from .views.referentiels.site_empotage import CreerSiteEmpotage, DeleteSiteEmpotage, ListeSiteEmpotage, ModifierSiteEmpotage
from .views.referentiels.type_document import CreerTypeDocument, DeleteTypeDocument, ListeTypeDocument, ModifierTypeDocument
from .views.users import UserListView, UserCreateView, UserUpdateView, UserDeleteView
from .views.dossier.liste import ListeDossier
from .views.dossier.create import CreerDossier
from .views.dossier.edit import ModifierDossier
from .views.dossier.detail import DetailDossier
from .views.dossier.actions import retrograder_dossier
from .views.payement import DashboardPaiementView, DetailPaiementView, ListePaiementView
from .views.conteneur.detail import DetailConteneur
from .views.conteneur.recherche import RechercheConteneur
from .views.document import (
    DocumentAjouterAjaxView, DocumentChangerStatutAjaxView, DocumentCreateView,
    DocumentListeView, DocumentRemplacerAjaxView, DocumentSupprimerAjaxView,
)
app_name = 'DashboardPersonnel'

urlpatterns = [
    path('accueil/', DashboardPersonnel, name='dashboard-personnel'),

    #PAYS
    path('pays/liste/', ListePays.as_view(), name='pays-liste'),
    path('pays/creer/', CreatePays.as_view(), name='pays-create'),
    path('pays/modifier/<uuid:pk>/', ModifierPays.as_view(), name='pays-update'),

    #COMMODITES
    path('commodites/liste/', ListeCommodites.as_view(), name='commodites-liste'),
    path('commodites/creer/', CreerCommodite.as_view(), name='commodites-create'),
    path('commodites/modifier/<uuid:pk>/', ModifierCommodite.as_view(), name='commodites-update'),
    path('commodites/supprimer/<uuid:pk>/', DeleteCommodite.as_view(), name='commodites-delete'),

    #POL
    path('pol/liste/', ListePOL.as_view(), name='pol-liste'),
    path('pol/creer/', CreerPOL.as_view(), name='pol-create'),
    path('pol/modifier/<uuid:pk>/', ModifierPOL.as_view(), name='pol-update'),
    path('pol/supprimer/<uuid:pk>/', DeletePOL.as_view(), name='pol-delete'),

    #POD
    path('pod/liste/', ListePOD.as_view(), name='pod-liste'),
    path('pod/creer/', CreerPOD.as_view(), name='pod-create'),
    path('pod/modifier/<uuid:pk>/', ModifierPOD.as_view(), name='pod-update'),
    path('pod/supprimer/<uuid:pk>/', DeletePOD.as_view(), name='pod-delete'),

    #COMPAGNIE MARITIME
    path('compagnie/liste/', ListeCompagnieMaritime.as_view(), name='compagnie-liste'),
    path('compagnie/creer/', CreerCompagnieMaritime.as_view(), name='compagnie-create'),
    path('compagnie/modifier/<uuid:pk>/', ModifierCompagnieMaritime.as_view(), name='compagnie-update'),
    path('compagnie/supprimer/<uuid:pk>/', DeleteCompagnieMaritime.as_view(), name='compagnie-delete'),

    #SITE DE SELECTION
    path('site-selection/liste/', ListeSiteSelection.as_view(), name='site-selection-liste'),
    path('site-selection/creer/', CreerSiteSelection.as_view(), name='site-selection-create'),
    path('site-selection/modifier/<uuid:pk>/', ModifierSiteSelection.as_view(), name='site-selection-update'),
    path('site-selection/supprimer/<uuid:pk>/', DeleteSiteSelection.as_view(), name='site-selection-delete'),

    #SITE D'EMPOTAGE
    path('site-empotage/liste/', ListeSiteEmpotage.as_view(), name='site-empotage-liste'),
    path('site-empotage/creer/', CreerSiteEmpotage.as_view(), name='site-empotage-create'),
    path('site-empotage/modifier/<uuid:pk>/', ModifierSiteEmpotage.as_view(), name='site-empotage-update'),
    path('site-empotage/supprimer/<uuid:pk>/', DeleteSiteEmpotage.as_view(), name='site-empotage-delete'),

    #UTILISATEUR
    path('users/liste/', UserListView.as_view(), name='user-list'),
    path('users/creer/', UserCreateView.as_view(), name='user-create'),
    path('users/modifier/<int:pk>/', UserUpdateView.as_view(), name='user-update'),
    path('users/supprimer/<int:pk>/', UserDeleteView.as_view(), name='user-delete'),

    #DOSSIER
    path('dossiers/liste/', ListeDossier.as_view(), name='dossier-liste'),
    path('dossiers/creer/', CreerDossier.as_view(), name='dossier-create'),
    path('dossiers/modifier/<uuid:pk>/', ModifierDossier.as_view(), name='dossier-update'),
    path('dossiers/<uuid:pk>/', DetailDossier.as_view(), name='dossier-detail'),
    path('dossiers/<uuid:dossier_id>/retrograder/', retrograder_dossier, name='dossier-retrograder'),

    #PAIEMENTS (suivi lecture seule, accès restreint via conteneurs.can_voir_paiements)
    path('paiements/accueil/', DashboardPaiementView.as_view(), name='dashboard-paiement'),
    path('paiements/liste/', ListePaiementView.as_view(), name='paiement-liste'),
    path('paiements/<uuid:pk>/', DetailPaiementView.as_view(), name='paiement-detail'),

    #CONTENEUR
    path('conteneurs/rechercher/', RechercheConteneur.as_view(), name='conteneur-recherche'),
    path('conteneurs/<uuid:pk>/', DetailConteneur.as_view(), name='conteneur-detail'),

    #TYPE DE DOCUMENT
    path('type-document/liste/', ListeTypeDocument.as_view(), name='type-document-liste'),
    path('type-document/creer/', CreerTypeDocument.as_view(), name='type-document-create'),
    path('type-document/modifier/<uuid:pk>/', ModifierTypeDocument.as_view(), name='type-document-update'),
    path('type-document/supprimer/<uuid:pk>/', DeleteTypeDocument.as_view(), name='type-document-delete'),

    #DOCUMENTS
    path('documents/liste/', DocumentListeView.as_view(), name='document-liste'),
    path('documents/ajouter/', DocumentCreateView.as_view(), name='document-create'),
    path('documents/<uuid:dossier_id>/ajouter/<uuid:type_document_id>/ajax/', DocumentAjouterAjaxView.as_view(), name='document-ajouter-ajax'),
    path('documents/<uuid:pk>/remplacer/ajax/', DocumentRemplacerAjaxView.as_view(), name='document-remplacer-ajax'),
    path('documents/<uuid:pk>/supprimer/ajax/', DocumentSupprimerAjaxView.as_view(), name='document-supprimer-ajax'),
    path('documents/<uuid:pk>/statut/ajax/', DocumentChangerStatutAjaxView.as_view(), name='document-statut-ajax'),
]
