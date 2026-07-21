from django.http import HttpRequest, HttpResponseRedirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from conteneurs.models import Dossier, Pays, Personnel
from conteneurs.forms import DossiersForm, DossiersMauritanieForm
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.mail import send_mail, EmailMultiAlternatives, EmailMessage
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from django.utils.translation import gettext as _
from django.db.models import Min, Max

@method_decorator(login_required, name='dispatch')
class DossierViewMauritanie(ListView):
    model = Dossier
    context_object_name = 'Dossier_list'
    template_name = 'pages/Dossier/Dossier_list_Mauritanie.html'

    def get_queryset(self):
        user = self.request.user
        queryset = Dossier.objects.all()
        # Récupérer l'année sélectionnée ou utiliser l'année en cours
        selected_year = self.request.GET.get('year', timezone.now().year)
        try:
            selected_year = int(selected_year)
        except (TypeError, ValueError):
            selected_year = timezone.now().year

        # Filtrer par année
        queryset = queryset.filter(date_creation__year=selected_year)
        pays = Pays.objects.filter(nom='Mauritanie').first()  # Récupérer l'objet Pays pour 'Nigeria'
        if pays:
            queryset = queryset.filter(pays=pays)

        statut = self.request.GET.get('statut')
        
         # Si l'utilisateur est admin, afficher seulement les dossiers du client reuse    
        if user.username == 'william':
            queryset = queryset.filter(client__nom='REUSE TRADING NV')
            
        if statut:
            queryset = queryset.filter(statut=statut)

        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(projet__icontains=search_query) |
                Q(TRD__icontains=search_query) |
                Q(booking__icontains=search_query)
            )
        return queryset.order_by('-date_creation')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nombre_dossiers'] = self.get_queryset().count()  # Nombre de dossiers
        dossiers = self.get_queryset()
        
        # Récupérer toutes les années disponibles (en fonction de Dossier et non Dossier2)
        years_range = Dossier.objects.aggregate(
            min_year=Min('date_creation__year'),
            max_year=Max('date_creation__year')
        )
        
        available_years = []
        if years_range['min_year'] and years_range['max_year']:
            available_years = range(years_range['max_year'], years_range['min_year'] - 1, -1)
        
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


@method_decorator(login_required, name='dispatch')
class DossierCreateMauritanieView(CreateView):
    model = Dossier
    form_class = DossiersMauritanieForm
    template_name = "pages/Dossier/Dossier_create_Mauritanie.html"
    success_url = reverse_lazy('Dossier_list_mauritanie')
    form_invalid_message = _("Oups, quelque chose s'est mal passé!")

    def get_form_valid_message(self):
        return _("{self.object} créé avec succès!")

    def form_valid(self, form):
        # Assigner la secrétaire connectée (utilisateur actuel)
        dossier = form.save(commit=False)
        dossier.secretaire = self.request.user
        pays_mauritanie = Pays.objects.get(nom="Mauritanie")  # Remplacer par le pays souhaité
        form.instance.pays = pays_mauritanie

        dossier.save()

        # Récupérer l'email de l'agent de sélection et des chefs
        agent_selection_email = dossier.agent_selection.email
        chefs_emails = [chef.email for chef in Personnel.objects.filter(Personnel_type='chef')]

        # Préparation de l'email
        subject = _('Nouveau dossier assigné')
        message = _(f"""
        <html>
            <body>
                <p>Un nouveau dossier <strong>{dossier.projet}</strong> pour {dossier.pays} vous a été assigné par : <strong>{self.request.user}</strong> à l'agent de sélection <strong>{dossier.agent_selection}</strong>.</p>
                <p>Vous pouvez consulter le dossier en vous rendant sur l'application : <a href="https://empotage-oils-of-africa.net/login/">Cliquez ici pour vous connecter</a>.</p>
            </body>
        </html>
        """)

        # Expéditeur : email de la secrétaire
        from_email = self.request.user.email

        # Liste des destinataires
        recipient_list = [agent_selection_email] + chefs_emails
        
        # Mail en copie
        cc_list = ["infos@smtla-sa.com","logistics@oils-of-africa.com"]


        # Création de l'email
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email,
            to=recipient_list,
            cc=cc_list
        )
        email.content_subtype = 'html'  # Spécifier le format HTML de l'email
        email.content_subtype = 'html'  # Spécifier le format HTML de l'email

        # Gestion des fichiers joints
        fichiers = self.request.FILES.getlist('fichiers')  # Récupérer tous les fichiers sélectionnés
        if fichiers:
            for fichier in fichiers:
                email.attach(fichier.name, fichier.read(), fichier.content_type)
        else:
            message += "<p><em>Aucun fichier joint n'a été ajouté.</em></p>"

        # Envoi de l'email
        email.send(fail_silently=False)

        # Message de succès après sauvegarde
        messages.success(self.request, _("ENREGISTREMENT DU DOSSIER AVEC SUCCÈS"))
        return super().form_valid(form)

    def form_invalid(self, form):
        # Afficher les erreurs dans la console pour debug
        print(form.errors)
        response = super().form_invalid(form)
        messages.error(self.request, _("ERREUR !!! Le dossier existe déjà"))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "post"
        context['action'] = "create"  # Ajouter une variable pour indiquer l'action
        return context

@method_decorator(login_required, name='dispatch')
class DossierUpdateMauritanieView(UpdateView):
    model = Dossier
    form_class = DossiersMauritanieForm
    template_name = "pages/Dossier/Dossier_create_Mauritanie.html"
    success_url = reverse_lazy('Dossier_list_mauritanie')

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Dossier, pk=pk)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()  # Passer l'instance à modifier
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Modification effectuée avec succès !"))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Erreur lors de la modification du dossier."))
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "post"
        context['action'] = "update"  # Ajouter une variable pour indiquer l'action
        return context

@method_decorator(login_required, name='dispatch')
class DossierDeleteMauritanieView(DeleteView):
    model = Dossier
    template_name = "pages/Dossier/Dossier_confirm_delete_Mauritanie.html"
    success_url = reverse_lazy('Dossier_list_mauritanie')
    form_invalid_message = _("Oups, quelque chose s'est mal passé lors de la suppression!")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, _("Le Dossier a été supprimé avec succès!"))
        return super().delete(request, *args, **kwargs)

    def get_object(self, **kwargs):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Dossier, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['method'] = "delete"
        return context

def dossier_detail_Mauritanie(request, pk):
    dossier = get_object_or_404(Dossier, pk=pk)
    return render(request, 'pages/Dossier/Dossier_detail_modal_Mauritanie.html', {'dossier': dossier})
