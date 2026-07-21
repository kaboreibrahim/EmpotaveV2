from django import forms
from django.db.models import Count, Q
from django.views.generic import ListView

from apps.conteneurs.models import Dossier

from ..mixins import ClientRequiredMixin

INPUT_CLASS = (
    'bg-surface-container-low border border-outline-variant rounded-lg px-3 py-2 '
    'text-body-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all'
)


class FiltreDossierForm(forms.Form):
    q = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Recherche (TRD, projet, booking...)',
            'class': 'w-full pl-10 pr-4 py-2 bg-surface-container-low border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all font-body-sm text-body-sm rounded-lg',
        }),
    )
    filtre_statut = forms.ChoiceField(label='', required=False, widget=forms.Select(attrs={'class': INPUT_CLASS}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['filtre_statut'].choices = [('', 'Tous les statuts'), *Dossier.STATUT_CHOICES]


class DossierListeView(ClientRequiredMixin, ListView):
    model = Dossier
    template_name = 'DashboardClient/dossier/liste.html'
    context_object_name = 'dossier_list'
    paginate_by = 12

    def get_filter_form(self):
        if not hasattr(self, '_filter_form'):
            self._filter_form = FiltreDossierForm(self.request.GET or None)
        return self._filter_form

    def get_base_queryset(self):
        return Dossier.objects.select_related(
            'Id_Pays', 'Id_POL', 'Id_POD',
        ).annotate(
            nb_iso=Count('isotanks', distinct=True),
            nb_flexi=Count('flexitanks', distinct=True),
        ).filter(id_client__user=self.request.user).order_by('-date_created')

    def get_queryset(self):
        queryset = self.get_base_queryset()
        form = self.get_filter_form()
        filters = form.cleaned_data if form.is_valid() else {}

        q = filters.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(TRD__icontains=q) | Q(projet__icontains=q) | Q(Booking__icontains=q)
            )

        filtre_statut = filters.get('filtre_statut', '').strip()
        if filtre_statut:
            queryset = queryset.filter(statut=filtre_statut)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtre_form'] = self.get_filter_form()

        base = self.get_base_queryset()
        context['total_dossiers'] = base.count()
        context['dossiers_en_attente'] = base.filter(statut='en_attente').count()
        context['dossiers_en_cours'] = base.filter(statut__in=['selection_en_cours', 'empotage_en_cours']).count()
        context['dossiers_termines'] = base.filter(statut='dossier_termine').count()

        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context
