from itertools import chain

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.http import Http404
from django.views.generic import DetailView

from apps.conteneurs.models import ConteneurCommunMixin, Dossier, ISOTanks

DETAIL_TEMPLATE = 'DashboardAgentSelection/dossier/detail.html'


class DossierDetailView(LoginRequiredMixin, DetailView):
    """Détail d'un dossier : rapport de sélection des conteneurs attribués."""
    model = Dossier
    template_name = DETAIL_TEMPLATE
    context_object_name = 'dossier'
    pk_url_kwarg = 'dossier_id'

    def get_queryset(self):
        qs = Dossier.objects.select_related(
            'Id_Pays', 'Id_POL', 'Id_POD', 'Id_CompagnieMaritime',
            'Id_SiteSelection', 'Id_SiteEmpotage', 'Id_Commodite', 'id_client',
            'Id_Agent_selection__user', 'Id_Agent_empotage__user',
        )
        if not self.request.user.is_superuser:
            qs = qs.filter(Id_Agent_selection__user=self.request.user)
        return qs

    def get_object(self, queryset=None):
        try:
            return super().get_object(queryset)
        except Dossier.DoesNotExist:
            raise Http404("Dossier introuvable ou non attribué à cet agent.")

    def get_conteneurs(self):
        dossier = self.object
        iso_qs = dossier.isotanks.all()
        flexi_qs = dossier.flexitanks.all()

        nature = self.request.GET.get('nature')
        if nature == 'iso':
            flexi_qs = flexi_qs.none()
        elif nature == 'flexitank':
            iso_qs = iso_qs.none()

        etat = self.request.GET.get('etat')
        if etat:
            iso_qs = iso_qs.filter(etat=etat)
            flexi_qs = flexi_qs.filter(etat=etat)

        return sorted(chain(iso_qs, flexi_qs), key=lambda c: c.reference)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dossier = self.object

        conteneurs = self.get_conteneurs()

        lignes = []
        for conteneur in conteneurs:
            nature = 'ISO Tank' if isinstance(conteneur, ISOTanks) else 'Flexitank'
            lignes.append({
                'objet': conteneur,
                'nature': nature,
            })

        total = dossier.isotanks.count() + dossier.flexitanks.count()
        nb_excellent = (
            dossier.isotanks.filter(etat='excellent').count()
            + dossier.flexitanks.filter(etat='excellent').count()
        )
        poids_total = (
            (dossier.isotanks.aggregate(total=Sum('poids_net'))['total'] or 0)
            + (dossier.flexitanks.aggregate(total=Sum('poids_net'))['total'] or 0)
        )

        repartition_etat = [
            {
                'valeur': valeur,
                'label': label,
                'nombre': (
                    dossier.isotanks.filter(etat=valeur).count()
                    + dossier.flexitanks.filter(etat=valeur).count()
                ),
            }
            for valeur, label in ConteneurCommunMixin.ETAT_CHOICES
        ]

        context.update({
            'conteneurs': lignes,
            'nombre_conteneurs': total,
            'nombre_affiches': len(lignes),
            'poids_total_net': poids_total,
            'poids_moyen_net': (poids_total / total) if total else 0,
            'taux_conformite': (nb_excellent / total * 100) if total else 0,
            'repartition_etat': repartition_etat,
            'etat_choices': ConteneurCommunMixin.ETAT_CHOICES,
            'nature_filtre': self.request.GET.get('nature', ''),
            'etat_filtre': self.request.GET.get('etat', ''),
        })
        return context
