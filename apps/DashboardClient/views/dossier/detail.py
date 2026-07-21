from itertools import chain

from django.db.models import Sum
from django.views.generic import DetailView

from apps.conteneurs.models import Dossier, ISOTanks

from ..document import construire_lignes_documents
from ..mixins import ClientRequiredMixin


class DossierDetailView(ClientRequiredMixin, DetailView):
    model = Dossier
    template_name = 'DashboardClient/dossier/detail.html'
    context_object_name = 'dossier'

    def get_queryset(self):
        return Dossier.objects.select_related(
            'Id_Pays', 'Id_POL', 'Id_POD', 'Id_Commodite', 'Id_CompagnieMaritime',
            'Id_SiteSelection', 'Id_SiteEmpotage',
        ).filter(id_client__user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dossier = self.object

        isotanks = dossier.isotanks.all()
        flexitanks = dossier.flexitanks.all()
        conteneurs = sorted(chain(isotanks, flexitanks), key=lambda c: c.reference)
        nb_conteneurs = len(conteneurs)
        nb_empotes = sum(1 for c in conteneurs if c.statut == 'empote')

        context['conteneurs'] = [
            {'objet': c, 'est_iso': isinstance(c, ISOTanks)}
            for c in conteneurs
        ]
        context['nb_conteneurs'] = nb_conteneurs
        context['nb_iso'] = isotanks.count()
        context['nb_flexi'] = flexitanks.count()
        context['nb_empotes'] = nb_empotes
        context['poids_total'] = (
            (isotanks.aggregate(total=Sum('poids_net'))['total'] or 0)
            + (flexitanks.aggregate(total=Sum('poids_net'))['total'] or 0)
        )
        context['progression_pct'] = round(nb_empotes / nb_conteneurs * 100) if nb_conteneurs else 0

        context.update(construire_lignes_documents(dossier))

        context['etapes_timeline'] = [
            {'label': 'Dossier créé', 'icone': 'folder_open', 'date': dossier.date_created, 'atteinte': True},
            {'label': 'Sélection', 'icone': 'fact_check', 'date': dossier.date_de_selection, 'atteinte': bool(dossier.date_de_selection)},
            {'label': 'Rapport soumis', 'icone': 'description', 'date': dossier.date_de_soumission_du_rapport, 'atteinte': bool(dossier.date_de_soumission_du_rapport)},
            {'label': 'Habillage & empotage', 'icone': 'inventory_2', 'date': dossier.date_de_empotage, 'atteinte': bool(dossier.date_de_empotage)},
            {'label': 'Terminé', 'icone': 'task_alt', 'date': None, 'atteinte': dossier.statut == 'dossier_termine'},
        ]
        return context
