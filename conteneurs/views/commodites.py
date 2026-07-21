from django.views.generic import ListView, CreateView,UpdateView,DeleteView
from conteneurs.models import Commodite
from conteneurs.forms import CommoditeForm
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from braces.views import FormMessagesMixin

from django.db.models import Q

@method_decorator(login_required, name='dispatch')
class CommoditeView(ListView):
    model = Commodite
    context_object_name = 'Commodite_list'
    template_name = 'pages/Commodite/Commodite_list.html'
    paginate_by = 10  # Définit le nombre d'éléments par page

    def get_queryset(self):
        queryset = Commodite.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(Q(nom_commodite__icontains=search) | Q(Date_ajout__icontains=search))
        return queryset.order_by('-Date_ajout')
             


@method_decorator(login_required, name='dispatch')
class CommoditeCreateView( CreateView):
    model = Commodite
    form_class = CommoditeForm
    template_name = "pages/Commodite/Commodite_create.html"
    success_url = reverse_lazy('Commodite_list')
    form_invalid_message = "Oups, quelque chose s'est mal passé!"

    def get_form_valid_message(self):
        return u"{0} crée avec succès!".format(self.object)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "ENREGISTREMENT DE Commodite")
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, "ERREUR !!! le Commodite ENTRE EXISTE DEJA")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "post"
        return context



@method_decorator(login_required, name='dispatch')
class CommoditeUpdateView( UpdateView):
    model = Commodite
    form_class = CommoditeForm
    template_name = "pages/Commodite/Commodite_create.html"
    success_url = reverse_lazy('Commodite_list')
    form_invalid_message = "Oups, quelque chose s'est mal passé!"

    def get_form_valid_message(self):
        return u"Modification effectuée avec succès!"

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Commodite, pk=pk)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object  # Pass the instance to the form
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "put"
        return context

@method_decorator(login_required, name='dispatch')
class CommoditeDeleteView( DeleteView):
    model = Commodite
    template_name = "pages/Commodite/Commodite_confirm_delete.html"
    success_url = reverse_lazy('Commodite_list')
    form_invalid_message = "Oups, quelque chose s'est mal passé lors de la suppression!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Le Commodite a été supprimé avec succès!")
        return super().delete(request, *args, **kwargs)

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Commodite, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "delete"
        return context
