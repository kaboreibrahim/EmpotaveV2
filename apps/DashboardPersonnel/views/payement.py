"""
apps/DashboardPersonnel/views/payement.py
Suivi des paiements côté Personnel : dossiers payés/non payés, détail, petit
dashboard. Lecture seule (la validation reste réservée au groupe Comptable,
voir apps/comptabiliteDashboard) — accès restreint à la permission Django
dédiée `conteneurs.can_voir_paiements`, à accorder au cas par cas via l'admin
(Utilisateurs > permissions) ou via un groupe dédié, sans ouvrir cette vue à
tout le Personnel.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q, Sum
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView

from apps.conteneurs.models import Dossier

DASHBOARD_TEMPLATE = 'DashboardPersonnel/pages/paiement/dashboard.html'
LISTE_TEMPLATE = 'DashboardPersonnel/pages/paiement/liste.html'
DETAIL_TEMPLATE = 'DashboardPersonnel/pages/paiement/detail.html'


class PaiementAccesRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Restreint le suivi des paiements à la permission `conteneurs.can_voir_paiements`.

    Non connecté -> redirection login. Connecté sans la permission -> 403.
    """
    permission_required = 'conteneurs.can_voir_paiements'


class DashboardPaiementView(PaiementAccesRequiredMixin, TemplateView):
    """Petit tableau de bord : compte des dossiers payés/en attente + montant du mois."""

    template_name = DASHBOARD_TEMPLATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Dossier.objects.all()

        total_dossiers = qs.count()
        total_payes = qs.filter(est_paye=True).count()
        total_en_attente = qs.filter(est_paye=False).count()

        context['total_dossiers'] = total_dossiers
        context['total_payes'] = total_payes
        context['total_en_attente'] = total_en_attente
        context['pct_payes'] = round(total_payes / total_dossiers * 100) if total_dossiers else 0

        maintenant = timezone.now()
        paiements = qs.filter(est_paye=True, montant_paiement__isnull=False)
        context['montant_total'] = paiements.aggregate(total=Sum('montant_paiement'))['total'] or 0
        context['montant_ce_mois'] = (
            paiements
            .filter(date_paiement__year=maintenant.year, date_paiement__month=maintenant.month)
            .aggregate(total=Sum('montant_paiement'))['total'] or 0
        )

        context['dossiers_en_attente'] = (
            qs.filter(est_paye=False).select_related('id_client__user').order_by('-date_created')[:8]
        )
        context['dossiers_payes_recents'] = (
            qs.filter(est_paye=True).select_related('id_client__user', 'utilisateur_paiement').order_by('-date_paiement')[:8]
        )
        return context


class ListePaiementView(PaiementAccesRequiredMixin, ListView):
    """Liste des dossiers, filtrable par statut de paiement (?paye=0 / ?paye=1) et recherche (?q=)."""

    model = Dossier
    template_name = LISTE_TEMPLATE
    context_object_name = 'dossiers'
    paginate_by = 25

    def get_queryset(self):
        qs = Dossier.objects.select_related('Id_Pays', 'id_client__user').order_by('-date_created')

        filtre = self.request.GET.get('paye')
        if filtre == '1':
            qs = qs.filter(est_paye=True)
        elif filtre == '0':
            qs = qs.filter(est_paye=False)

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(TRD__icontains=q)
                | Q(projet__icontains=q)
                | Q(Booking__icontains=q)
                | Q(id_client__user__username__icontains=q)
                | Q(id_client__user__first_name__icontains=q)
                | Q(id_client__user__last_name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtre_paye'] = self.request.GET.get('paye', '')
        context['q'] = self.request.GET.get('q', '')
        return context


class DetailPaiementView(PaiementAccesRequiredMixin, DetailView):
    """Détail d'un dossier centré sur les informations de paiement (lecture seule)."""

    model = Dossier
    template_name = DETAIL_TEMPLATE
    context_object_name = 'dossier'

    def get_queryset(self):
        return Dossier.objects.select_related(
            'Id_Pays', 'id_client__user',
            'Id_Agent_selection__user', 'Id_Agent_empotage__user',
            'utilisateur_paiement',
        )
