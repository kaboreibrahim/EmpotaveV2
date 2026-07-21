from django.db.models import Q
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from apps.referentiels.models import Commodite, Pays

from django import forms

from ..mixins import AjaxCreateMixin, DeleteMessageMixin, FormMessageMixin, ModulePermissionRequiredMixin


def build_sigle(nom):
    return nom.strip()[:2].upper()


class FiltrePaysForm(forms.Form):
    q = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Rechercher par nom, sigle ou pays...',
            'class': 'w-full pl-10 pr-4 py-2 bg-surface-container-low border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all font-body-sm text-body-sm rounded-lg',
        }),
    )
    filtre_pays = forms.ChoiceField(label='', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pays_choices = Pays.objects.order_by('nom').values_list('id', 'nom')
        self.fields['filtre_pays'].choices = [('', 'Tous les pays'), *pays_choices]


class ListeCommodites(ModulePermissionRequiredMixin, ListView):
    model = Commodite
    template_name = 'DashboardPersonnel/pages/commodites/liste.html'
    context_object_name = 'commodites_list'
    paginate_by = 12

    def get_filter_form(self):
        if not hasattr(self, '_filter_form'):
            self._filter_form = FiltrePaysForm(self.request.GET or None)
        return self._filter_form

    def get_queryset(self):
        queryset = Commodite.objects.select_related('Id_Pays').order_by('nom')
        form = self.get_filter_form()
        filters = form.cleaned_data if form.is_valid() else {}

        q = filters.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(nom__icontains=q)
                | Q(sig__icontains=q)
                | Q(Id_Pays__nom__icontains=q)
            )

        filtre_pays = filters.get('filtre_pays', '').strip()
        if filtre_pays:
            queryset = queryset.filter(Id_Pays_id=filtre_pays)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_commodites'] = Commodite.objects.count()
        context['pays_avec_commodites'] = Pays.objects.filter(commodites__isnull=False).distinct().count()
        context['derniere_maj'] = (
            Commodite.objects.order_by('-date_created').values_list('date_created', flat=True).first()
        )
        context['filtre_pays_form'] = self.get_filter_form()

        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()

        view_mode = self.request.GET.get('view')
        context['view_mode'] = 'cards' if view_mode == 'cards' else 'table'

        table_params = self.request.GET.copy()
        table_params.pop('page', None)
        table_params['view'] = 'table'
        context['table_querystring'] = table_params.urlencode()

        cards_params = self.request.GET.copy()
        cards_params.pop('page', None)
        cards_params['view'] = 'cards'
        context['cards_querystring'] = cards_params.urlencode()
        return context

class CreerCommodite(ModulePermissionRequiredMixin, AjaxCreateMixin, FormMessageMixin, CreateView):
    model = Commodite
    template_name = 'DashboardPersonnel/pages/commodites/create.html'
    fields = ['nom', 'icon', 'Id_Pays']
    success_url = reverse_lazy('DashboardPersonnel:commodites-liste')
    success_message = "La commodite « %(nom)s » a ete ajoutee avec succes."

    def form_valid(self, form):
        form.instance.sig = build_sigle(form.cleaned_data['nom'])
        return super().form_valid(form)

class ModifierCommodite(ModulePermissionRequiredMixin, FormMessageMixin, UpdateView):
    model = Commodite
    template_name = 'DashboardPersonnel/pages/commodites/edit.html'
    fields = ['nom', 'icon', 'Id_Pays']
    success_url = reverse_lazy('DashboardPersonnel:commodites-liste')
    success_message = "La commodite « %(nom)s » a ete modifiee avec succes."

    def form_valid(self, form):
        form.instance.sig = build_sigle(form.cleaned_data['nom'])
        return super().form_valid(form)

class DeleteCommodite(ModulePermissionRequiredMixin, DeleteMessageMixin, DeleteView):
    model = Commodite
    template_name = 'DashboardPersonnel/pages/commodites/delete.html'
    success_url = reverse_lazy('DashboardPersonnel:commodites-liste')
    success_message = "La commodite « %(object)s » a ete supprimee avec succes."
