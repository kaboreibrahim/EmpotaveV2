from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.generic import DetailView, ListView

from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.conteneurs.models import Dossier
from apps.notification.services import NotificationService

from ..mixins import ComptableRequiredMixin, est_comptable

LISTE_TEMPLATE = 'comptabiliteDashboard/dossier/liste.html'
DETAIL_TEMPLATE = 'comptabiliteDashboard/dossier/detail.html'


class DossierListeComptableView(ComptableRequiredMixin, ListView):
    """Liste des dossiers, filtrable par statut de paiement (?paye=0 / ?paye=1)."""

    model = Dossier
    template_name = LISTE_TEMPLATE
    context_object_name = 'dossiers'
    paginate_by = 25

    def get_queryset(self):
        qs = Dossier.objects.select_related('Id_Pays', 'id_client__user').order_by('-date_created')
        filtre = self.request.GET.get('paye')
        if filtre == '1':
            qs = qs.filter(est_paye=True)
        elif filtre == '0':
            qs = qs.filter(est_paye=False)

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(TRD__icontains=q)
                | Q(projet__icontains=q)
                | Q(Booking__icontains=q)
                | Q(id_client__user__username__icontains=q)
                | Q(id_client__user__first_name__icontains=q)
                | Q(id_client__user__last_name__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtre_paye'] = self.request.GET.get('paye', '')
        context['q'] = self.request.GET.get('q', '')
        return context


class DossierDetailComptableView(ComptableRequiredMixin, DetailView):
    model = Dossier
    template_name = DETAIL_TEMPLATE
    context_object_name = 'dossier'

    def get_queryset(self):
        return Dossier.objects.select_related(
            'Id_Pays', 'Id_POL', 'Id_POD', 'id_client__user',
            'Id_Agent_selection__user', 'Id_Agent_empotage__user', 'Id_Personnel__user',
            'utilisateur_paiement',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['peut_valider'] = est_comptable(self.request.user)
        return context


def _lire_donnees_paiement(request):
    """Extrait et valide date/montant/commentaire/preuve depuis un POST de formulaire paiement.

    Retourne (donnees, erreur) : `erreur` est un message à afficher si la saisie est invalide,
    auquel cas `donnees` vaut None.
    """
    date_paiement = parse_datetime(request.POST.get('date_paiement', ''))
    if date_paiement is None:
        return None, "Veuillez renseigner une date de paiement valide."
    if timezone.is_naive(date_paiement):
        date_paiement = timezone.make_aware(date_paiement)

    commentaire = request.POST.get('commentaire_paiement', '').strip()
    if not commentaire:
        return None, "Veuillez renseigner un commentaire de paiement."

    montant = None
    montant_brut = request.POST.get('montant_paiement', '').strip()
    if montant_brut:
        try:
            montant = Decimal(montant_brut.replace(',', '.'))
        except InvalidOperation:
            return None, "Le montant du paiement n'est pas un nombre valide."
        if montant < 0:
            return None, "Le montant du paiement ne peut pas être négatif."

    preuve = request.FILES.get('preuve_paiement')
    if preuve and not preuve.name.lower().endswith('.pdf'):
        return None, "La preuve de paiement doit être un fichier PDF."

    return {
        'date_paiement': date_paiement,
        'commentaire': commentaire,
        'montant': montant,
        'preuve': preuve,
    }, None


def valider_paiement(request, dossier_id):
    """Valide le paiement d'un dossier : date, commentaire, comptable, déblocage automatique."""
    dossier = get_object_or_404(Dossier, id=dossier_id)

    if request.method != 'POST':
        return redirect('comptabiliteDashboard:dossier-detail', pk=dossier.id)

    if not est_comptable(request.user):
        raise PermissionDenied("Seul le service comptable peut valider un paiement.")

    if dossier.est_paye:
        messages.info(request, "Ce dossier est déjà payé.")
        return redirect('comptabiliteDashboard:dossier-detail', pk=dossier.id)

    donnees, erreur = _lire_donnees_paiement(request)
    if erreur:
        messages.error(request, erreur)
        return redirect('comptabiliteDashboard:dossier-detail', pk=dossier.id)

    dossier.valider_paiement(
        request.user, commentaire=donnees['commentaire'], date_paiement=donnees['date_paiement'],
        montant=donnees['montant'], preuve=donnees['preuve'],
    )
    log_action(dossier, AuditLog.ACTION_UPDATE, extra={'evenement': 'paiement_valide'})

    NotificationService.notify_payment_validated(dossier)

    messages.success(request, f"Paiement du dossier {dossier.projet} validé, le dossier est débloqué.")
    return redirect('comptabiliteDashboard:dossier-detail', pk=dossier.id)


def modifier_paiement(request, dossier_id):
    """Modifie un paiement déjà validé : date, montant, commentaire, preuve PDF."""
    dossier = get_object_or_404(Dossier, id=dossier_id)

    if request.method != 'POST':
        return redirect('comptabiliteDashboard:dossier-detail', pk=dossier.id)

    if not est_comptable(request.user):
        raise PermissionDenied("Seul le service comptable peut modifier un paiement.")

    if not dossier.est_paye:
        messages.error(request, "Ce dossier n'est pas encore payé : utilisez « Valider le paiement ».")
        return redirect('comptabiliteDashboard:dossier-detail', pk=dossier.id)

    donnees, erreur = _lire_donnees_paiement(request)
    if erreur:
        messages.error(request, erreur)
        return redirect('comptabiliteDashboard:dossier-detail', pk=dossier.id)

    ancienne_preuve = dossier.preuve_paiement
    dossier.valider_paiement(
        request.user, commentaire=donnees['commentaire'], date_paiement=donnees['date_paiement'],
        montant=donnees['montant'], preuve=donnees['preuve'],
    )
    if donnees['preuve'] and ancienne_preuve:
        ancienne_preuve.delete(save=False)

    log_action(dossier, AuditLog.ACTION_UPDATE, extra={'evenement': 'paiement_modifie'})
    messages.success(request, f"Paiement du dossier {dossier.projet} mis à jour.")
    return redirect('comptabiliteDashboard:dossier-detail', pk=dossier.id)
