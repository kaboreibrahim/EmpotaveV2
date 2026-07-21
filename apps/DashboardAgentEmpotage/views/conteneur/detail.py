from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import render
from django.views import View

from apps.conteneurs.models import Flexitanks, ISOTanks

DETAIL_TEMPLATE = 'DashboardAgentEmpotage/dossier_empotage/conteneur_detail.html'
SELECT_RELATED = ('dossier', 'dossier__Id_Pays')


def _get_conteneur_ou_404(request, pk):
    """Récupère le conteneur (ISO Tank ou Flexitank), restreint aux dossiers de l'agent connecté."""
    qs_iso = ISOTanks.objects.select_related(*SELECT_RELATED)
    qs_flexi = Flexitanks.objects.select_related(*SELECT_RELATED)
    if not request.user.is_superuser:
        qs_iso = qs_iso.filter(dossier__Id_Agent_empotage__user=request.user)
        qs_flexi = qs_flexi.filter(dossier__Id_Agent_empotage__user=request.user)

    conteneur = qs_iso.filter(pk=pk).first()
    if conteneur is not None:
        return conteneur, True
    conteneur = qs_flexi.filter(pk=pk).first()
    if conteneur is not None:
        return conteneur, False
    raise Http404("Conteneur introuvable ou non attribué à cet agent.")


class ConteneurDetailView(LoginRequiredMixin, View):
    """Détail d'un conteneur, côté agent d'empotage (spécifications + photos de sélection et d'empotage)."""

    def get(self, request, pk):
        conteneur, est_iso = _get_conteneur_ou_404(request, pk)

        photos_selection = [
            ('Avant', conteneur.photo_devant),
            ('Derrière', conteneur.photo_derriere),
            ('Intérieure', conteneur.photo_interieur),
            ('Latéral droit', conteneur.photo_lateral_droit),
            ('Latéral gauche', conteneur.photo_lateral_gauche),
        ]
        photos_empotage = [
            ('Début', conteneur.photo_debut),
            ('Pendant', conteneur.photo_pendant),
            ('Fin', conteneur.photo_fin),
        ]
        if est_iso:
            photos_empotage += [
                ('Plomb amateur 1', conteneur.photoPlombAmateur1),
                ('Plomb amateur 2', conteneur.photoPlombAmateur2),
                ('Plomb amateur 3', conteneur.photoPlombAmateur3),
                ('Plombs Oils 1', conteneur.photo_plombs_oils1),
                ('Plombs Oils 2', conteneur.photo_plombs_oils2),
            ]
        else:
            photos_empotage += [
                ('Flexitank', conteneur.photoFlextank),
                ('Heating pad', conteneur.Photoheatingpad),
                ('Plombs amateur', conteneur.plombs_amateur_photo),
                ('Plombs Oils', conteneur.photo_plombs_oils),
            ]

        return render(request, DETAIL_TEMPLATE, {
            'conteneur': conteneur,
            'est_iso': est_iso,
            'photos_selection': photos_selection,
            'photos_empotage': photos_empotage,
        })
