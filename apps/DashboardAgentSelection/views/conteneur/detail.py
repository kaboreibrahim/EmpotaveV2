from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import render
from django.views import View

from apps.conteneurs.models import Flexitanks, ISOTanks

DETAIL_TEMPLATE = 'DashboardAgentSelection/dossier/conteneur_detail.html'
SELECT_RELATED = ('dossier', 'dossier__Id_Pays')


def _get_conteneur_ou_404(request, pk):
    """Récupère le conteneur (ISO Tank ou Flexitank), restreint aux dossiers de l'agent connecté."""
    qs_iso = ISOTanks.objects.select_related(*SELECT_RELATED)
    qs_flexi = Flexitanks.objects.select_related(*SELECT_RELATED)
    if not request.user.is_superuser:
        qs_iso = qs_iso.filter(dossier__Id_Agent_selection__user=request.user)
        qs_flexi = qs_flexi.filter(dossier__Id_Agent_selection__user=request.user)

    conteneur = qs_iso.filter(pk=pk).first()
    if conteneur is not None:
        return conteneur, True
    conteneur = qs_flexi.filter(pk=pk).first()
    if conteneur is not None:
        return conteneur, False
    raise Http404("Conteneur introuvable ou non attribué à cet agent.")


class ConteneurDetailView(LoginRequiredMixin, View):
    """Détail d'un conteneur, côté agent de sélection (spécifications + photos de sélection)."""

    def get(self, request, pk):
        conteneur, est_iso = _get_conteneur_ou_404(request, pk)

        photos_selection = [
            ('Avant', conteneur.photo_devant),
            ('Derrière', conteneur.photo_derriere),
            ('Intérieure', conteneur.photo_interieur),
            ('Latéral droit', conteneur.photo_lateral_droit),
            ('Latéral gauche', conteneur.photo_lateral_gauche),
        ]

        return render(request, DETAIL_TEMPLATE, {
            'conteneur': conteneur,
            'est_iso': est_iso,
            'photos_selection': photos_selection,
        })
