from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.views.generic import TemplateView

from apps.conteneurs.models import Flexitanks, ISOTanks

RECHERCHE_TEMPLATE = 'DashboardPersonnel/pages/conteneur/recherche.html'
SELECT_RELATED = ('dossier', 'dossier__Id_Pays')


class RechercheConteneur(LoginRequiredMixin, TemplateView):
    """Recherche un conteneur (ISO Tank ou Flexitank) par référence, numéros de plombs,
    numéro de Flexitank ou numéro de heating pad."""
    template_name = RECHERCHE_TEMPLATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()
        context['q'] = q
        context['resultats'] = self._rechercher(q) if q else []
        return context

    def _rechercher(self, q):
        filtre_iso = (
            Q(reference__icontains=q)
            | Q(plombAmateur1__icontains=q)
            | Q(plombAmateur2__icontains=q)
            | Q(plombAmateur3__icontains=q)
            | Q(Plombs_oils1__icontains=q)
            | Q(Plombs_oils2__icontains=q)
        )
        filtre_flexi = (
            Q(reference__icontains=q)
            | Q(numeroFlextank__icontains=q)
            | Q(Numeroheatingpad__icontains=q)
            | Q(plombs_amateur__icontains=q)
            | Q(Plombs_oils__icontains=q)
        )

        isotanks = ISOTanks.objects.select_related(*SELECT_RELATED).filter(filtre_iso)
        flexitanks = Flexitanks.objects.select_related(*SELECT_RELATED).filter(filtre_flexi)

        resultats = (
            [{'objet': c, 'est_iso': True} for c in isotanks]
            + [{'objet': c, 'est_iso': False} for c in flexitanks]
        )
        resultats.sort(key=lambda r: r['objet'].reference)
        return resultats
