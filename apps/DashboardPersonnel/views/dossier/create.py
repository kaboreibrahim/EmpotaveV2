from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView

from apps.conteneurs.models import Dossier
from apps.conteneurs.stock_client import StockServiceIndisponible, creer_sortie_brouillon
from apps.referentiels.models import (
    POD, POL, CompagnieMaritime, Commodite, Pays, SiteEmpotage, SiteSelection,
)
from apps.notification.services import NotificationService, notifier
from apps.users.models import Agent_empotage, Agent_selection, Client, Personnel

from ..mixins import FormMessageMixin, ModulePermissionRequiredMixin

COPIE_CREATION_DOSSIER = ['infos@oils-of-africa.com']
EMAIL_CREATION_TEMPLATE = 'DashboardPersonnel/emails/dossier_cree.html'


def _options(queryset, label_fn=str, pays_fn=None):
    options = []
    for obj in queryset:
        item = {'value': str(obj.pk), 'label': label_fn(obj)}
        if pays_fn:
            pays_id = pays_fn(obj)
            item['pays'] = str(pays_id) if pays_id else None
        options.append(item)
    return options


def _lieu_label(obj):
    return f"{obj.nom} — {obj.lieu}"


def _client_label(client):
    return client.user.get_full_name() or client.user.username


class DossierForm(forms.ModelForm):
    class Meta:
        model = Dossier
        fields = [
            'TRD', 'projet', 'Booking', 'type_conteneur',
            'Id_Pays', 'Id_POL', 'Id_POD', 'Id_Commodite', 'Id_CompagnieMaritime',
            'Id_SiteSelection', 'Id_SiteEmpotage', 'id_client',
            'Id_Agent_selection', 'Id_Agent_empotage', 'Id_Agent_operationel',
            'commentaire_creation',
        ]
        widgets = {
            'commentaire_creation': forms.HiddenInput(),
        }


class DossierOptionsMixin:
    """Fournit les options (JSON) des selects cherchables du formulaire Dossier."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pays_options'] = _options(Pays.objects.order_by('nom'))
        context['pol_options'] = _options(
            POL.objects.select_related('Id_Pays').order_by('nom'), _lieu_label, lambda o: o.Id_Pays_id
        )
        context['pod_options'] = _options(
            POD.objects.select_related('Id_Pays').order_by('nom'), _lieu_label, lambda o: o.Id_Pays_id
        )
        context['commodite_options'] = _options(
            Commodite.objects.order_by('nom'), pays_fn=lambda o: o.Id_Pays_id
        )
        context['compagnie_options'] = _options(
            CompagnieMaritime.objects.select_related('Id_Pays').order_by('nom'), _lieu_label, lambda o: o.Id_Pays_id
        )
        context['site_selection_options'] = _options(
            SiteSelection.objects.select_related('Id_Pays').order_by('nom'), _lieu_label, lambda o: o.Id_Pays_id
        )
        context['site_empotage_options'] = _options(
            SiteEmpotage.objects.select_related('Id_Pays').order_by('nom'), _lieu_label, lambda o: o.Id_Pays_id
        )
        context['client_options'] = _options(
            Client.objects.select_related('user').order_by('user__username'),
            _client_label, lambda c: c.user.pays_id
        )
        context['agent_selection_options'] = _options(
            Agent_selection.objects.select_related('user'), pays_fn=lambda a: a.user.pays_id
        )
        context['agent_empotage_options'] = _options(
            Agent_empotage.objects.select_related('user'), pays_fn=lambda a: a.user.pays_id
        )
        context['agent_operationnel_options'] = _options(
            Personnel.objects.select_related('user'), pays_fn=lambda p: p.user.pays_id
        )
        return context


class CreerDossier(ModulePermissionRequiredMixin, DossierOptionsMixin, FormMessageMixin, CreateView):
    model = Dossier
    form_class = DossierForm
    template_name = 'DashboardPersonnel/pages/dossier/create.html'
    success_url = reverse_lazy('DashboardPersonnel:dossier-liste')
    success_message = "Le dossier « %(TRD)s » a ete cree avec succes."

    def form_valid(self, form):
        if not form.cleaned_data.get('commentaire_creation', '').strip():
            form.add_error(None, "Veuillez renseigner un commentaire de création.")
            return self.form_invalid(form)

        form.instance.Id_Personnel = getattr(self.request.user, 'personel', None)
        response = super().form_valid(form)
        dossier = self.object
        self._creer_brouillon_stock(dossier)
        self._notifier_agent_selection(dossier)
        notifier(
            dossier.id_client.user,
            f"Votre dossier {dossier.TRD} — {dossier.projet} a été créé et va être traité.",
        )
        NotificationService.notify_dossier_created(dossier)
        if dossier.Id_Agent_empotage:
            notifier(
                dossier.Id_Agent_empotage.user,
                f"Un nouveau dossier vous a été attribué : {dossier.TRD} — {dossier.projet}.",
            )
        return response

    def _creer_brouillon_stock(self, dossier):
        """Cree le brouillon de sortie cote oils-stock-api (option a du dossier
        d'integration : ne bloque jamais la creation du Dossier — une panne
        reseau se rattrape plus tard via `retry_sorties_brouillons`).

        La societe cliente n'est plus choisie sur le formulaire : elle est
        deduite automatiquement depuis le Client (compte de suivi empotage)
        deja selectionne, voir Client.resoudre_client_entreprise()."""
        client_entreprise = dossier.id_client.resoudre_client_entreprise()
        if not client_entreprise or not client_entreprise.stock_client_id:
            return
        dossier.Id_ClientEntreprise = client_entreprise
        try:
            sortie = creer_sortie_brouillon(
                client_id=client_entreprise.stock_client_id,
                projet=dossier.projet,
                trd=dossier.TRD,
                date_sortie=timezone.now().date(),
            )
        except StockServiceIndisponible as exc:
            dossier.save(update_fields=['Id_ClientEntreprise'])
            messages.warning(
                self.request,
                f"Le dossier a été créé, mais le brouillon de sortie stock n'a pas pu être créé : {exc}. "
                "Il sera créé automatiquement plus tard.",
            )
            return
        dossier.sortie_stock_id = sortie['id']
        dossier.sortie_stock_reference = sortie['reference']
        dossier.save(update_fields=['Id_ClientEntreprise', 'sortie_stock_id', 'sortie_stock_reference'])

    def _notifier_agent_selection(self, dossier):
        agent = dossier.Id_Agent_selection
        if not agent or not agent.user.email:
            return

        agent_nom = agent.user.get_full_name() or agent.user.username
        texte_body = (
            f"Bonjour {agent_nom},\n\n"
            f"Un nouveau dossier vous a été attribué : {dossier.projet} (TRD : {dossier.TRD}), "
            f"pour le client {dossier.id_client} — {dossier.Id_Pays.nom}.\n\n"
            "Merci de vous connecter à https://empotage-oils-of-africa.net/login/ "
            "pour démarrer la sélection des conteneurs."
        )

        email = EmailMultiAlternatives(
            subject=f"Nouveau dossier attribué — {dossier.projet} ({dossier.TRD})",
            body=texte_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[agent.user.email],
            cc=COPIE_CREATION_DOSSIER,
        )
        email.attach_alternative(
            render_to_string(EMAIL_CREATION_TEMPLATE, {
                'dossier': dossier,
                'agent_selection': agent_nom,
                'logo_url': self.request.build_absolute_uri(static('img/logo.png')),
            }),
            'text/html',
        )
        try:
            email.send()
        except Exception as exc:
            messages.warning(
                self.request,
                f"Le dossier a été créé, mais l'email de notification à l'agent de sélection n'a pas pu être envoyé : {exc}",
            )
