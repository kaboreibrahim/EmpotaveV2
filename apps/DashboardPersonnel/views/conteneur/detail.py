from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.shortcuts import render
from django.views import View

from apps.audit.models import AuditLog
from apps.conteneurs.models import Flexitanks, ISOTanks

SELECT_RELATED = (
    'dossier', 'dossier__Id_Pays', 'dossier__Id_POL', 'dossier__Id_POD',
    'dossier__Id_CompagnieMaritime', 'dossier__id_client__user',
)


def _get_conteneur_ou_404(pk):
    conteneur = ISOTanks.objects.select_related(*SELECT_RELATED).filter(pk=pk).first()
    if conteneur is not None:
        return conteneur, True
    conteneur = Flexitanks.objects.select_related(*SELECT_RELATED).filter(pk=pk).first()
    if conteneur is not None:
        return conteneur, False
    raise Http404("Conteneur introuvable.")


class DetailConteneur(LoginRequiredMixin, View):
    template_name = 'DashboardPersonnel/pages/conteneur/detail.html'

    def get(self, request, pk):
        conteneur, est_iso = _get_conteneur_ou_404(pk)

        # Photos prises lors de la sélection du conteneur
        photos_selection = [
            ('Avant', conteneur.photo_devant),
            ('Derrière', conteneur.photo_derriere),
            ('Intérieure', conteneur.photo_interieur),
            ('Latéral droit', conteneur.photo_lateral_droit),
            ('Latéral gauche', conteneur.photo_lateral_gauche),
        ]

        # Photos prises lors de l'empotage (habillage, plombs, scellés)
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

        content_type = ContentType.objects.get_for_model(type(conteneur))
        historique = (
            AuditLog.objects
            .filter(content_type=content_type, object_id=str(conteneur.pk))
            .select_related('user')
            .order_by('-created_at')
        )

        return render(request, self.template_name, {
            'conteneur': conteneur,
            'est_iso': est_iso,
            'photos_selection': photos_selection,
            'photos_empotage': photos_empotage,
            'historique': historique,
        })
