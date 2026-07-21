from itertools import chain

from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum
from django.views.generic import DetailView

from apps.audit.models import AuditLog
from apps.conteneurs.models import Dossier, ISOTanks

from ..document import construire_lignes_documents
from ..mixins import ModulePermissionRequiredMixin


class DetailDossier(ModulePermissionRequiredMixin, DetailView):
    model = Dossier
    template_name = 'DashboardPersonnel/pages/dossier/detail.html'
    context_object_name = 'dossier'

    def get_queryset(self):
        return Dossier.objects.select_related(
            'Id_Pays', 'Id_POL', 'Id_POD', 'Id_Commodite', 'Id_CompagnieMaritime',
            'Id_SiteSelection', 'Id_SiteEmpotage',
            'id_client__user', 'Id_Agent_selection__user', 'Id_Agent_empotage__user', 'Id_Personnel__user',
        )

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

        content_type = ContentType.objects.get_for_model(Dossier)
        context['historique'] = (
            AuditLog.objects
            .filter(content_type=content_type, object_id=str(dossier.pk))
            .select_related('user')
            .order_by('-created_at')
        )
        return context
