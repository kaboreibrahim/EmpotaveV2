from django.db.models import Count, Q
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy

from apps.referentiels.models import POD, POL, Pays

from ..mixins import AjaxCreateMixin, FormMessageMixin, ModulePermissionRequiredMixin


class ListePays(ModulePermissionRequiredMixin, ListView):
    model = Pays
    template_name = 'DashboardPersonnel/pages/pays/liste.html'
    context_object_name = 'pays_list'
    paginate_by = 10

    def get_queryset(self):
        return (
            Pays.objects
            .annotate(nb_ports=Count('pols', distinct=True) + Count('pods', distinct=True))
            .order_by('nom')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_ports'] = POL.objects.count() + POD.objects.count()
        context['pays_avec_ports'] = (
            Pays.objects.filter(Q(pols__isnull=False) | Q(pods__isnull=False)).distinct().count()
        )
        context['derniere_maj'] = (
            Pays.objects.order_by('-date_created').values_list('date_created', flat=True).first()
        )
        return context


class CreatePays(ModulePermissionRequiredMixin, AjaxCreateMixin, FormMessageMixin, CreateView):
    model = Pays
    template_name = 'DashboardPersonnel/pages/pays/create.html'
    fields = ['nom', 'drapeau']
    success_url = reverse_lazy('DashboardPersonnel:pays-liste')
    success_message = "Le pays « %(nom)s » a ete ajoute avec succes."


class ModifierPays(ModulePermissionRequiredMixin, FormMessageMixin, UpdateView):
    model = Pays
    template_name = 'DashboardPersonnel/pages/pays/edit.html'
    fields = ['nom', 'drapeau']
    success_url = reverse_lazy('DashboardPersonnel:pays-liste')
    success_message = "Le pays « %(nom)s » a ete modifie avec succes."


