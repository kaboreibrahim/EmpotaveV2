import os
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.staticfiles import finders
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from xhtml2pdf import pisa

from apps.facturation.forms import FactureForm, LigneFactureFormSet
from apps.facturation.models import Facture


def _qs_factures():
    return Facture.objects.select_related(
        "client", "banque", "incoterm", "produit", "port_livraison", "destination",
    ).prefetch_related("lignes")


# --------------------------------------------------------------------------- #
# Liste
# --------------------------------------------------------------------------- #
class FactureListView(LoginRequiredMixin, ListView):
    model = Facture
    template_name = "facturation/facture_list.html"
    context_object_name = "factures"
    paginate_by = 25

    def get_queryset(self):
        qs = _qs_factures()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(numero__icontains=q)
                | Q(numero_proforma__icontains=q)
                | Q(ref_client__icontains=q)
                | Q(ref_dossier__icontains=q)
                | Q(client__user__first_name__icontains=q)
                | Q(client__user__last_name__icontains=q)
                | Q(incoterm__code__icontains=q)
            )
        client = self.request.GET.get("client")
        if client:
            qs = qs.filter(client_id=client)
        statut = self.request.GET.get("statut")
        if statut in Facture.Statut.values:
            qs = qs.filter(statut=statut)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["statut"] = self.request.GET.get("statut", "")
        return ctx


# --------------------------------------------------------------------------- #
# Détail
# --------------------------------------------------------------------------- #
class FactureDetailView(LoginRequiredMixin, DetailView):
    model = Facture
    template_name = "facturation/facture_detail.html"
    context_object_name = "facture"

    def get_queryset(self):
        return _qs_factures()


# --------------------------------------------------------------------------- #
# Création / modification (facture + lignes en une seule page)
# --------------------------------------------------------------------------- #
class _FactureFormMixin(LoginRequiredMixin):
    model = Facture
    form_class = FactureForm
    template_name = "facturation/facture_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if "formset" not in kwargs:
            ctx["formset"] = LigneFactureFormSet(
                self.request.POST or None, instance=self.object
            )
        return ctx

    def form_valid(self, form):
        formset = LigneFactureFormSet(self.request.POST, instance=self.object)
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
        messages.success(self.request, f"{self.object.get_statut_display()} {self.object.reference} enregistrée.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("facturation:detail", kwargs={"pk": self.object.pk})


class _ProformaSeulementMixin:
    """Une facture validée n'est plus supprimable (son n° IN… doit rester dans la séquence)."""

    def dispatch(self, request, *args, **kwargs):
        facture = get_object_or_404(Facture, pk=kwargs["pk"])
        if not facture.est_proforma:
            messages.error(request, f"La facture {facture.reference} est validée : elle ne peut pas être supprimée.")
            return redirect("facturation:detail", pk=facture.pk)
        return super().dispatch(request, *args, **kwargs)


class FactureCreateView(_FactureFormMixin, CreateView):
    pass


class FactureUpdateView(_FactureFormMixin, UpdateView):
    """Proformas et factures validées sont modifiables ; le n° et le statut ne changent pas."""


# --------------------------------------------------------------------------- #
# Suppression (soft delete via SafeDeleteModel)
# --------------------------------------------------------------------------- #
class FactureDeleteView(LoginRequiredMixin, _ProformaSeulementMixin, DeleteView):
    model = Facture
    template_name = "facturation/facture_confirm_delete.html"
    success_url = reverse_lazy("facturation:liste")

    def form_valid(self, form):
        messages.success(self.request, f"Proforma {self.object.reference} supprimée.")
        return super().form_valid(form)


# --------------------------------------------------------------------------- #
# Validation client : proforma -> facture
# --------------------------------------------------------------------------- #
@login_required
@require_POST
def valider_facture(request, pk):
    facture = get_object_or_404(Facture, pk=pk)
    if not facture.est_proforma:
        messages.error(request, f"{facture.reference} est déjà une facture.")
        return redirect("facturation:detail", pk=pk)
    proforma = facture.numero_proforma
    facture.valider()
    messages.success(request, f"Proforma {proforma} validée : facture {facture.numero} créée.")
    return redirect("facturation:detail", pk=pk)


# --------------------------------------------------------------------------- #
# PDF (xhtml2pdf)
# --------------------------------------------------------------------------- #
def _nb(valeur):
    """Decimal('2.00') -> '2' ; Decimal('18.50') -> '18.5'."""
    texte = f"{valeur:f}"
    return texte.rstrip("0").rstrip(".") if "." in texte else texte


def _montant(valeur):
    """1637268 -> '1 637 268,00'."""
    return f"{Decimal(valeur):,.2f}".replace(",", " ").replace(".", ",")


def link_callback(uri, rel):
    """Résout les URLs /static/ et /media/ en chemins disque pour xhtml2pdf."""
    path = None
    if settings.MEDIA_URL and uri.startswith(settings.MEDIA_URL):
        path = os.path.join(settings.MEDIA_ROOT, uri[len(settings.MEDIA_URL):])
    elif settings.STATIC_URL and uri.startswith(settings.STATIC_URL):
        relatif = uri[len(settings.STATIC_URL):]
        path = finders.find(relatif)
        if not path and settings.STATIC_ROOT:
            path = os.path.join(settings.STATIC_ROOT, relatif)
    else:
        return uri
    return path if path and os.path.isfile(path) else uri


def _contexte_pdf(facture):
    lignes = [
        {
            "designation": l.designation,
            "tva": f"{_nb(l.tva_taux)} %",
            "pu_ht": _montant(l.pu_ht),
            "quantite": _nb(l.quantite),
            "total_ht": _montant(l.total_ht),
        }
        for l in facture.lignes.all()
    ]
    return {
        "facture": facture,
        "lignes": lignes,
        "total_ht_fcfa": _montant(facture.total_ht_fcfa),
        "total_ttc_fcfa": _montant(facture.total_ttc_fcfa),
        "total_ht_eur": _montant(facture.total_ht_eur),
        "total_ttc_eur": _montant(facture.total_ttc_eur),
        "taux_change": f"{facture.taux_change:f}".replace(".", ","),
    }


@login_required
def facture_pdf(request, pk):
    """PDF dans le navigateur ; ajouter ?download=1 pour forcer le téléchargement."""
    facture = get_object_or_404(_qs_factures(), pk=pk)
    html = render_to_string("facturation/facture_pdf.html", _contexte_pdf(facture))

    response = HttpResponse(content_type="application/pdf")
    mode = "attachment" if request.GET.get("download") else "inline"
    response["Content-Disposition"] = f'{mode}; filename="{facture.reference}.pdf"'

    resultat = pisa.CreatePDF(html, dest=response, link_callback=link_callback, encoding="utf-8")
    if resultat.err:
        return HttpResponse("Erreur lors de la génération du PDF.", status=500)
    return response


@login_required
def envoyer_facture_email(request, pk):
    """Envoie la facture par email aux destinataires comptabilité."""
    facture = get_object_or_404(_qs_factures(), pk=pk)

    # Générer le PDF
    html = render_to_string("facturation/facture_pdf.html", _contexte_pdf(facture))
    pdf_response = HttpResponse(content_type="application/pdf")
    resultat = pisa.CreatePDF(html, dest=pdf_response, link_callback=link_callback, encoding="utf-8")

    if resultat.err:
        messages.error(request, "Erreur lors de la génération du PDF.")
        return redirect("facturation:detail", pk=pk)

    # Destinataires
    destinataires = ["comptabilite@oils-of-africa.com", "serge.debetou@oils-of-africa.com","it@otl-bulkliquid.com"]

    # Préparer l'email
    nom_client = facture.client.user.get_full_name() or facture.client.user.get_username()
    document = f"{facture.get_statut_display()} {facture.reference}"
    email = EmailMessage(
        subject=f"{document} - {nom_client}",
        body=f"""Bonjour,

Veuillez trouver ci-joint la {document.lower()} pour le client {nom_client}.

Référence client : {facture.ref_client}
Montant TTC : {facture.total_ttc_fcfa} FCFA

Cordialement.""",
        to=destinataires,
    )
    email.attach(f"{facture.reference}.pdf", pdf_response.content, "application/pdf")

    try:
        email.send()
        messages.success(request, f"{document} envoyée par email à {', '.join(destinataires)}.")
    except Exception as e:
        messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")

    return redirect("facturation:detail", pk=pk)