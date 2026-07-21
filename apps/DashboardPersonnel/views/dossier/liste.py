from django import forms
from django.db.models import Count, Q
from django.views.generic import ListView

from apps.conteneurs.models import Dossier
from apps.referentiels.models import Pays
from apps.users.models import Client

from ..mixins import ModulePermissionRequiredMixin

INPUT_CLASS = (
    'bg-surface-container-low border border-outline-variant rounded-lg px-3 py-2 '
    'text-body-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all'
)


class FiltreDossierForm(forms.Form):
    q = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Recherche globale (TRD, projet, booking, client...)',
            'class': 'w-full pl-10 pr-4 py-2 bg-surface-container-low border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all font-body-sm text-body-sm rounded-lg',
        }),
    )
    filtre_pays = forms.ChoiceField(
        label='', required=False,
        widget=forms.Select(attrs={'class': INPUT_CLASS, 'id': 'id_filtre_pays'}),
    )
    filtre_client = forms.ChoiceField(
        label='', required=False,
        widget=forms.Select(attrs={'class': INPUT_CLASS, 'id': 'id_filtre_client'}),
    )
    filtre_statut = forms.ChoiceField(label='', required=False, widget=forms.Select(attrs={'class': INPUT_CLASS}))
    filtre_type_conteneur = forms.ChoiceField(
        label='', required=False,
        choices=[('', 'Tous types'), ('iso', 'ISO Tank'), ('flexi', 'Flexitank')],
        widget=forms.Select(attrs={'class': INPUT_CLASS}),
    )
    date_debut = forms.DateField(label='', required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}))
    date_fin = forms.DateField(label='', required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': INPUT_CLASS}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pays_choices = Pays.objects.order_by('nom').values_list('id', 'nom')
        self.fields['filtre_pays'].choices = [('', 'Tous les pays'), *pays_choices]

        clients_queryset = Client.objects.select_related('user').order_by('user__username')
        filtre_pays = self.data.get('filtre_pays') if self.is_bound else None
        if filtre_pays:
            clients_queryset = clients_queryset.filter(user__pays_id=filtre_pays)

        client_choices = [
            (client.pk, client.user.get_full_name() or client.user.username)
            for client in clients_queryset
        ]
        self.fields['filtre_client'].choices = [('', 'Tous les clients'), *client_choices]
        self.fields['filtre_statut'].choices = [('', 'Tous les statuts'), *Dossier.STATUT_CHOICES]


class ListeDossier(ModulePermissionRequiredMixin, ListView):
    model = Dossier
    template_name = 'DashboardPersonnel/pages/dossier/liste.html'
    context_object_name = 'dossier_list'
    paginate_by = 12

    def get_filter_form(self):
        if not hasattr(self, '_filter_form'):
            self._filter_form = FiltreDossierForm(self.request.GET or None)
        return self._filter_form

    def get_queryset(self):
        queryset = Dossier.objects.select_related(
            'Id_Pays', 'Id_POL', 'Id_POD', 'id_client__user',
        ).annotate(
            nb_iso=Count('isotanks', distinct=True),
            nb_flexi=Count('flexitanks', distinct=True),
        ).order_by('-date_created')
        form = self.get_filter_form()
        filters = form.cleaned_data if form.is_valid() else {}

        q = filters.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(TRD__icontains=q)
                | Q(projet__icontains=q)
                | Q(Booking__icontains=q)
                | Q(id_client__user__username__icontains=q)
                | Q(id_client__user__first_name__icontains=q)
                | Q(id_client__user__last_name__icontains=q)
            )

        filtre_pays = filters.get('filtre_pays', '').strip()
        if filtre_pays:
            queryset = queryset.filter(Id_Pays_id=filtre_pays)

        filtre_client = filters.get('filtre_client', '').strip()
        if filtre_client:
            queryset = queryset.filter(id_client_id=filtre_client)

        filtre_statut = filters.get('filtre_statut', '').strip()
        if filtre_statut:
            queryset = queryset.filter(statut=filtre_statut)

        filtre_type_conteneur = filters.get('filtre_type_conteneur', '').strip()
        if filtre_type_conteneur == 'iso':
            queryset = queryset.filter(nb_iso__gt=0)
        elif filtre_type_conteneur == 'flexi':
            queryset = queryset.filter(nb_flexi__gt=0)

        date_debut = filters.get('date_debut')
        if date_debut:
            queryset = queryset.filter(date_created__date__gte=date_debut)

        date_fin = filters.get('date_fin')
        if date_fin:
            queryset = queryset.filter(date_created__date__lte=date_fin)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtre_form'] = self.get_filter_form()
        context['total_dossiers'] = Dossier.objects.count()
        context['dossiers_en_attente'] = Dossier.objects.filter(statut='en_attente').count()
        context['dossiers_en_cours'] = Dossier.objects.filter(
            statut__in=['selection_en_cours', 'empotage_en_cours']
        ).count()
        context['dossiers_termines'] = Dossier.objects.filter(statut='dossier_termine').count()
        context['dossiers_annules'] = Dossier.objects.filter(statut='annulé').count()

        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context
