from django import forms
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.referentiels.models import Pays, SiteSelection

from ..mixins import AjaxCreateMixin, DeleteMessageMixin, FormMessageMixin, ModulePermissionRequiredMixin


class FiltreSiteSelectionForm(forms.Form):
    q = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Rechercher par nom, lieu ou pays...',
            'class': 'w-full pl-10 pr-4 py-2 bg-surface-container-low border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all font-body-sm text-body-sm rounded-lg',
        }),
    )
    filtre_pays = forms.ChoiceField(label='', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pays_choices = Pays.objects.order_by('nom').values_list('id', 'nom')
        self.fields['filtre_pays'].choices = [('', 'Tous les pays'), *pays_choices]


class ListeSiteSelection(ModulePermissionRequiredMixin, ListView):
    model = SiteSelection
    template_name = 'DashboardPersonnel/pages/site_selection/liste.html'
    context_object_name = 'site_selection_list'
    paginate_by = 12

    def get_filter_form(self):
        if not hasattr(self, '_filter_form'):
            self._filter_form = FiltreSiteSelectionForm(self.request.GET or None)
        return self._filter_form

    def get_queryset(self):
        queryset = SiteSelection.objects.select_related('Id_Pays').order_by('nom')
        form = self.get_filter_form()
        filters = form.cleaned_data if form.is_valid() else {}

        q = filters.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(nom__icontains=q)
                | Q(lieu__icontains=q)
                | Q(Id_Pays__nom__icontains=q)
            )

        filtre_pays = filters.get('filtre_pays', '').strip()
        if filtre_pays:
            queryset = queryset.filter(Id_Pays_id=filtre_pays)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_sites'] = SiteSelection.objects.count()
        context['pays_avec_sites'] = Pays.objects.filter(sites_selection__isnull=False).distinct().count()
        context['derniere_maj'] = SiteSelection.objects.order_by('-date_created').values_list('date_created', flat=True).first()
        context['filtre_pays_form'] = self.get_filter_form()
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class CreerSiteSelection(ModulePermissionRequiredMixin, AjaxCreateMixin, FormMessageMixin, CreateView):
    model = SiteSelection
    template_name = 'DashboardPersonnel/pages/site_selection/create.html'
    fields = ['nom', 'contact', 'lieu', 'Id_Pays']
    success_url = reverse_lazy('DashboardPersonnel:site-selection-liste')
    success_message = "Le site de selection « %(nom)s » a ete ajoute avec succes."


class ModifierSiteSelection(ModulePermissionRequiredMixin, FormMessageMixin, UpdateView):
    model = SiteSelection
    template_name = 'DashboardPersonnel/pages/site_selection/edit.html'
    fields = ['nom', 'contact', 'lieu', 'Id_Pays']
    success_url = reverse_lazy('DashboardPersonnel:site-selection-liste')
    success_message = "Le site de selection « %(nom)s » a ete modifie avec succes."


class DeleteSiteSelection(ModulePermissionRequiredMixin, DeleteMessageMixin, DeleteView):
    model = SiteSelection
    template_name = 'DashboardPersonnel/pages/site_selection/delete.html'
    success_url = reverse_lazy('DashboardPersonnel:site-selection-liste')
    success_message = "Le site de selection « %(object)s » a ete supprime avec succes."
