from django import forms
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.referentiels.models import CompagnieMaritime, Pays

from ..mixins import AjaxCreateMixin, DeleteMessageMixin, FormMessageMixin, ModulePermissionRequiredMixin


class FiltreCompagnieMaritimeForm(forms.Form):
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


class ListeCompagnieMaritime(ModulePermissionRequiredMixin, ListView):
    model = CompagnieMaritime
    template_name = 'DashboardPersonnel/pages/compagnie/liste.html'
    context_object_name = 'compagnie_list'
    paginate_by = 10

    def get_filter_form(self):
        if not hasattr(self, '_filter_form'):
            self._filter_form = FiltreCompagnieMaritimeForm(self.request.GET or None)
        return self._filter_form

    def get_queryset(self):
        queryset = CompagnieMaritime.objects.select_related('Id_Pays').order_by('nom')
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
        context['total_compagnies'] = CompagnieMaritime.objects.count()
        context['pays_avec_compagnies'] = Pays.objects.filter(compagnies_maritimes__isnull=False).distinct().count()
        context['derniere_maj'] = CompagnieMaritime.objects.order_by('-date_created').values_list('date_created', flat=True).first()
        context['filtre_pays_form'] = self.get_filter_form()
        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class CreerCompagnieMaritime(ModulePermissionRequiredMixin, AjaxCreateMixin, FormMessageMixin, CreateView):
    model = CompagnieMaritime
    template_name = 'DashboardPersonnel/pages/compagnie/create.html'
    fields = ['nom', 'lieu', 'Id_Pays']
    success_url = reverse_lazy('DashboardPersonnel:compagnie-liste')
    success_message = "La compagnie « %(nom)s » a ete ajoutee avec succes."


class ModifierCompagnieMaritime(ModulePermissionRequiredMixin, FormMessageMixin, UpdateView):
    model = CompagnieMaritime
    template_name = 'DashboardPersonnel/pages/compagnie/edit.html'
    fields = ['nom', 'lieu', 'Id_Pays']
    success_url = reverse_lazy('DashboardPersonnel:compagnie-liste')
    success_message = "La compagnie « %(nom)s » a ete modifiee avec succes."


class DeleteCompagnieMaritime(ModulePermissionRequiredMixin, DeleteMessageMixin, DeleteView):
    model = CompagnieMaritime
    template_name = 'DashboardPersonnel/pages/compagnie/delete.html'
    success_url = reverse_lazy('DashboardPersonnel:compagnie-liste')
    success_message = "La compagnie « %(object)s » a ete supprimee avec succes."