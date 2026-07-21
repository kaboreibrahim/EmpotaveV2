from django.views.generic import ListView, CreateView,UpdateView,DeleteView
from conteneurs.models import CompagnieMaritime
from conteneurs.forms import CompagnieMaritimeForm
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from braces.views import FormMessagesMixin

from django.db.models import Q

@method_decorator(login_required, name='dispatch')
class CompagnieMaritimeView( ListView):
    model = CompagnieMaritime
    context_object_name = 'CompagnieMaritime_list'
    template_name = 'pages/CompagnieMaritime/CompagnieMaritime_list.html'
    paginate_by = 10  # Définit le nombre d'éléments par page

    def get_queryset(self):
        queryset = CompagnieMaritime.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(Q(nom_compagnie_maritime__icontains=search) | Q(Date_ajout__icontains=search))
        return queryset.order_by('-Date_ajout')
             


@method_decorator(login_required, name='dispatch')
class CompagnieMaritimeCreateView( CreateView):
    model = CompagnieMaritimeForm
    form_class = CompagnieMaritimeForm
    template_name = "pages/CompagnieMaritime/CompagnieMaritime_create.html"
    success_url = reverse_lazy('CompagnieMaritime_list')
    form_invalid_message = "Oups, quelque chose s'est mal passé!"

    def get_form_valid_message(self):
        return u"{0} crée avec succès!".format(self.object)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "ENREGISTREMENT DE CompagnieMaritime")
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, "ERREUR !!! le CompagnieMaritime ENTRE EXISTE DEJA")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "post"
        return context



@method_decorator(login_required, name='dispatch')
class CompagnieMaritimeUpdateView( UpdateView):
    model = CompagnieMaritimeForm
    form_class = CompagnieMaritimeForm
    template_name = "pages/CompagnieMaritime/CompagnieMaritime_create.html"
    success_url = reverse_lazy('CompagnieMaritime_list')
    form_invalid_message = "Oups, quelque chose s'est mal passé!"

    def get_form_valid_message(self):
        return u"Modification effectuée avec succès!"

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        return get_object_or_404(CompagnieMaritime, pk=pk)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object  # Pass the instance to the form
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "put"
        return context

@method_decorator(login_required, name='dispatch')
class CompagnieMaritimeDeleteView( DeleteView):
    model = CompagnieMaritime
    template_name = "pages/CompagnieMaritime/CompagnieMaritime_confirm_delete.html"
    success_url = reverse_lazy('CompagnieMaritime_list')
    form_invalid_message = "Oups, quelque chose s'est mal passé lors de la suppression!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Le CompagnieMaritimeForm a été supprimé avec succès!")
        return super().delete(request, *args, **kwargs)

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        return get_object_or_404(CompagnieMaritime, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "delete"
        return context
