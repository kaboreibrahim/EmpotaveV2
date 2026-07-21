from django.http import Http404
from django.shortcuts import render
from django.views import View

from apps.conteneurs.models import Flexitanks, ISOTanks

from .mixins import ClientRequiredMixin

DETAIL_TEMPLATE = 'DashboardClient/conteneur/detail.html'
SELECT_RELATED = (
    'dossier', 'dossier__Id_Pays', 'dossier__Id_POL', 'dossier__Id_POD', 'dossier__Id_CompagnieMaritime',
)


def _get_conteneur_du_client(request, pk):
    """Récupère un conteneur (ISO Tank ou Flexitank) appartenant à un dossier du client connecté."""
    qs_iso = ISOTanks.objects.select_related(*SELECT_RELATED).filter(dossier__id_client__user=request.user)
    qs_flexi = Flexitanks.objects.select_related(*SELECT_RELATED).filter(dossier__id_client__user=request.user)

    conteneur = qs_iso.filter(pk=pk).first()
    if conteneur is not None:
        return conteneur, True
    conteneur = qs_flexi.filter(pk=pk).first()
    if conteneur is not None:
        return conteneur, False
    raise Http404("Conteneur introuvable.")


class ConteneurDetailView(ClientRequiredMixin, View):
    """Détail en lecture seule d'un conteneur (spécifications + photos de sélection et d'empotage)."""

    def get(self, request, pk):
        conteneur, est_iso = _get_conteneur_du_client(request, pk)

        photos_selection = [
            ('Avant', conteneur.photo_devant),
            ('Derrière', conteneur.photo_derriere),
            ('Intérieure', conteneur.photo_interieur),
            ('Latéral droit', conteneur.photo_lateral_droit),
            ('Latéral gauche', conteneur.photo_lateral_gauche),
        ]

        photos_empotage = [
            ('Pendant empotage', conteneur.photo_pendant),
            ('Fin empotage', conteneur.photo_fin),
        ]
        if est_iso:
            photos_empotage += [
                ('Plomb amateur 1', conteneur.photoPlombAmateur1),
                ('Plomb amateur 2', conteneur.photoPlombAmateur2),
                ('Plomb amateur 3', conteneur.photoPlombAmateur3),
                ('Plombs oils 1', conteneur.photo_plombs_oils1),
                ('Plombs oils 2', conteneur.photo_plombs_oils2),
            ]
        else:
            photos_empotage += [
                ('Heating pad', conteneur.Photoheatingpad),
                ('Flexitank', conteneur.photoFlextank),
                ('Plombs amateur', conteneur.plombs_amateur_photo),
                ('Plombs oils', conteneur.photo_plombs_oils),
            ]

        return render(request, DETAIL_TEMPLATE, {
            'conteneur': conteneur,
            'est_iso': est_iso,
            'photos_selection': photos_selection,
            'photos_empotage': photos_empotage,
        })
