from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.views.generic import ListView

from apps.conteneurs.models import Dossier

LISTE_TEMPLATE = 'DashboardAgentEmpotage/dossier_empotage/liste.html'
LISTE_TERMINER_TEMPLATE = 'DashboardAgentEmpotage/dossier_empotage/liste_terminer.html'

# Dossiers en cours d'empotage (page "Dossiers") vs. empotage finalisé
# (page "Dossiers Terminés", cf. DossierListeTerminerView plus bas).
STATUTS_EN_COURS = ('empotage_en_cours',)
STATUTS_TERMINES = ('dossier_termine',)


class DossierListeView(LoginRequiredMixin, ListView):
    """Dossiers attribués à l'agent d'empotage connecté, encore en cours d'empotage."""
    model = Dossier
    template_name = LISTE_TEMPLATE
    context_object_name = 'dossiers'
    paginate_by = 10

    def get_base_queryset(self):
        qs = Dossier.objects.select_related(
            'Id_Pays', 'Id_POL', 'Id_POD', 'Id_CompagnieMaritime',
            'Id_SiteSelection', 'Id_SiteEmpotage', 'Id_Commodite', 'id_client',
        ).annotate(
            nombre_conteneurs=Count('isotanks', distinct=True) + Count('flexitanks', distinct=True)
        ).filter(statut__in=STATUTS_EN_COURS)

        if not self.request.user.is_superuser:
            qs = qs.filter(Id_Agent_empotage__user=self.request.user)
        return qs

    def get_queryset(self):
        qs = self.get_base_queryset().order_by('-date_created')
        statut = self.request.GET.get('statut')
        if statut in STATUTS_EN_COURS:
            qs = qs.filter(statut=statut)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = self.get_base_queryset()
        context['statut_choices'] = [
            (valeur, label) for valeur, label in Dossier.STATUT_CHOICES if valeur in STATUTS_EN_COURS
        ]
        context['statut_filtre'] = self.request.GET.get('statut', '')
        context['total_dossiers'] = base_qs.count()
        context['total_empotage_en_cours'] = base_qs.filter(statut='empotage_en_cours').count()
        return context


class DossierListeTerminerView(LoginRequiredMixin, ListView):
    """Dossiers dont l'empotage est finalisé."""
    model = Dossier
    template_name = LISTE_TERMINER_TEMPLATE
    context_object_name = 'dossiers'
    paginate_by = 10

    def get_base_queryset(self):
        qs = Dossier.objects.select_related(
            'Id_Pays', 'Id_POL', 'Id_POD', 'Id_CompagnieMaritime',
            'Id_SiteSelection', 'Id_SiteEmpotage', 'Id_Commodite', 'id_client',
        ).annotate(
            nombre_conteneurs=Count('isotanks', distinct=True) + Count('flexitanks', distinct=True)
        ).filter(statut__in=STATUTS_TERMINES)

        if not self.request.user.is_superuser:
            qs = qs.filter(Id_Agent_empotage__user=self.request.user)
        return qs

    def get_queryset(self):
        qs = self.get_base_queryset().order_by('-date_created')
        statut = self.request.GET.get('statut')
        if statut in STATUTS_TERMINES:
            qs = qs.filter(statut=statut)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = self.get_base_queryset()
        context['statut_choices'] = [
            (valeur, label) for valeur, label in Dossier.STATUT_CHOICES if valeur in STATUTS_TERMINES
        ]
        context['statut_filtre'] = self.request.GET.get('statut', '')
        context['total_dossiers'] = base_qs.count()
        context['total_termines'] = base_qs.filter(statut='dossier_termine').count()
        return context
