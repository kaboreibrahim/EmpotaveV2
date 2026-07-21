from django.http import HttpRequest, HttpResponseRedirect
from django.views.generic import ListView, CreateView,UpdateView,DeleteView,DetailView
from conteneurs.models import *
from conteneurs.forms import *
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect,render
from django.core.paginator import Paginator
from braces.views import FormMessagesMixin
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from django.db.models import Min, Max

 

class DossierView2(ListView):
    model = Dossier2
    context_object_name = 'dossiers_by_month'
    template_name = 'pages/Dossier2/Dossier_list.html'

    def get_queryset(self):
        queryset = Dossier2.objects.all()
        
        # Récupérer l'année sélectionnée ou utiliser l'année en cours
        selected_year = self.request.GET.get('year', timezone.now().year)
        try:
            selected_year = int(selected_year)
        except (TypeError, ValueError):
            selected_year = timezone.now().year

        # Filtrer par année
        queryset = queryset.filter(date_creation__year=selected_year)
        
        # Filtres existants
        statut = self.request.GET.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
            
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(projet__icontains=search_query) | 
                Q(TRD__icontains=search_query) | 
                Q(client__name__icontains=search_query)
            )
        
        return queryset.order_by('-date_creation')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dossiers = self.get_queryset()
        
        # Récupérer toutes les années disponibles
        years_range = Dossier2.objects.aggregate(
            min_year=Min('date_creation__year'),
            max_year=Max('date_creation__year')
        )
        
        available_years = []
        if years_range['min_year'] and years_range['max_year']:
            available_years = range(years_range['max_year'], 
                                 years_range['min_year'] - 1, -1)
        
        # Grouper les dossiers par mois
        dossiers_by_month = {}
        for dossier in dossiers:
            month_year = dossier.date_creation.strftime('%B %Y')
            if month_year not in dossiers_by_month:
                dossiers_by_month[month_year] = []
            dossiers_by_month[month_year].append(dossier)
        
        context['dossiers_by_month'] = dossiers_by_month
        context['available_years'] = available_years
        context['selected_year'] = int(self.request.GET.get('year', timezone.now().year))
        return context
 
from django.core.mail import EmailMessage
@method_decorator(login_required, name='dispatch')
class DossierCreateView2(CreateView):
    model = Dossier2
    form_class = Dossiers2Form
    template_name = "pages/Dossier2/Dossier_create.html"
    success_url = reverse_lazy('Dossier_list2')
    form_invalid_message = "Oups, quelque chose s'est mal passé!"

    def get_form_valid_message(self):
        return u"{0} crée avec succès!".format(self.object)

    def form_valid(self, form):
        # Assigner la secrétaire connectée (utilisateur actuel) avant de sauvegarder
        dossier = form.save(commit=False)
        dossier.save()
        # Message de succès après sauvegarde
        messages.success(self.request, "ENREGISTREMENT DU DOSSIER AVEC SUCCESS")
        return super().form_valid(form)

    def form_invalid(self, form):
        print(form.errors)  # Affiche les erreurs dans la console pour debug
        response = super().form_invalid(form)
        messages.error(self.request, "ERREUR !!! le Dossier ENTRE EXISTE DEJA")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "post"
        return context

@method_decorator(login_required, name='dispatch')
class DossierUpdateView2( UpdateView):
    model = Dossier2
    form_class = Dossiers2Form
    template_name = "pages/Dossier2/Dossier_create_modifier.html"
    success_url = reverse_lazy('Dossier_list2')
    form_invalid_message = "Oups, quelque chose s'est mal passé!"

    def get_form_valid_message(self):
        return u"Modification effectuée avec succès!"

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Dossier2, pk=pk)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object  # Pass the instance to the form
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "put"
        return context

@method_decorator(login_required, name='dispatch')
class DossierDeleteView2( DeleteView):
    model = Dossier2
    template_name = "pages/Dossier2/Dossier_confirm_delete.html"
    success_url = reverse_lazy('Dossier_list')
    form_invalid_message = "Oups, quelque chose s'est mal passé lors de la suppression!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Le Dossier a été supprimé avec succès!")
        return super().delete(request, *args, **kwargs)

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Dossier2, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "delete"
        return context

def dossier_detail(request, pk):
    dossier = get_object_or_404(Dossier2, pk=pk)
    return render(request, 'pages/Dossier2/Dossier_detail_modal.html', {'dossier': dossier})


def menu_sous_dossier (request,pk):
    dossier = get_object_or_404(Dossier2, pk=pk)
    cont_facture=Document_Facture.objects.filter(dossier=dossier).count()
    cont_autre_document=AutreDocument.objects.filter(dossier=dossier).count()
    cont_images=Images.objects.filter(dossier=dossier).count()

    return render( request, 'pages/Dossier2/menu_sous_dossier.html', {'dossier':dossier, 
                                                                    'cont_facture':cont_facture,
                                                                    'cont_autre_document':cont_autre_document,
                                                                    'cont_images':cont_images})

######################################  DOSSIER FACTURE #######################################
#liste des facture

def facture_list (request,pk):
    dossier = get_object_or_404(Dossier2, pk=pk)
    factures = Document_Facture.objects.filter(dossier=dossier)
    return render( request, 'pages/Dossier2/facture_list.html' ,{'dossier': dossier, 'factures': factures})

# ajouter des factures
def facture_create (request,pk):
    dossier = get_object_or_404(Dossier2, pk=pk)
    form = DocumentFactureForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        facture = form.save(commit=False)
        facture.dossier = dossier
        facture.save()
        messages.success(request, "Facture ajoutée avec succès!")
        return redirect('facture_list', pk=dossier.pk)

    return render(request, 'pages/Dossier2/facture_create.html', {'form': form, 'dossier': dossier})

###################################### AUTRE DOSSIER #######################################

# list des AUTRE DOSSIER

def autre_dossier_list (request,pk):
    dossier= get_object_or_404(Dossier2,pk=pk)
    autre_documents=AutreDocument.objects.filter(dossier=dossier)
    return render( request, 'pages/Dossier2/autre_dossier_list.html',{'autre_documents':autre_documents ,'dossier':dossier})

#ajouter des AUTRE DOSSIER

def autre_dossier_create (request,pk):
    dossier=get_object_or_404(Dossier2,pk=pk)
    form = AutreDocumentForm(request.POST or None ,request.FILES or None)
    
    if form.is_valid():
        autre_dossier=form.save(commit=False)
        autre_dossier.dossier=dossier
        autre_dossier.save()
        messages.success(request, "Autre dossier ajoutée avec succès !")
        return redirect('autre_dossier_list', pk=dossier.pk)
    return render( request ,'pages/Dossier2/autre_dossier_create.html',{'form': form, 'dossier': dossier})
###################################### images & video  #######################################

# list images

def images_list (request,pk):
    dossier= get_object_or_404(Dossier2,pk=pk)
    images=Images.objects.filter(dossier=dossier)
    return render( request, 'pages/Dossier2/images_list.html',{'images':images,'dossier':dossier})

# create videos and images

def images_create (request,pk):
    dossier=get_object_or_404(Dossier2,pk=pk)
    form = ImagesForm(request.POST or None ,request.FILES or None)
    
    if form.is_valid():
        images=form.save(commit=False)
        images.dossier=dossier
        images.save()
        messages.success(request, "Image ajoutée avec succès !")
        return redirect('images_list', pk=dossier.pk)
    return render( request ,'pages/Dossier2/images_create.html',{'form': form, 'dossier': dossier})