import os
from decimal import Decimal
 
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
  
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
 
 
from apps.facturation.models import Incoterm
from apps.facturation.forms import IncotermForm
from apps.facturation.models import Facture
# --------------------------------------------------------------------------- #
# Incoterms (liste, ajout, détail, modification, suppression)
# --------------------------------------------------------------------------- #
class IncotermListView(LoginRequiredMixin, ListView):
    model = Incoterm
    template_name = "incoterm/incoterm_list.html"
    context_object_name = "incoterms"
    paginate_by = 25
 
    def get_queryset(self):
        qs = Incoterm.objects.annotate(
            nb_factures=Count("facture", filter=Q(facture__deleted__isnull=True), distinct=True)
        ).order_by("code")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(libelle__icontains=q))
        return qs
 
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx
 
 
class IncotermDetailView(LoginRequiredMixin, DetailView):
    model = Incoterm
    template_name = "incoterm/incoterm_detail.html"
    context_object_name = "incoterm"
 
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        factures = Facture.objects.filter(incoterm=self.object).select_related("client")
        ctx["nb_factures"] = factures.count()
        ctx["factures"] = factures[:10]
        return ctx
 
 
class IncotermCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Incoterm
    form_class = IncotermForm
    template_name = "incoterm/incoterm_form.html"
    success_message = "Incoterm %(code)s enregistré."
 
    def get_success_url(self):
        return reverse_lazy("facturation:incoterm_detail", kwargs={"pk": self.object.pk})
 
 
class IncotermUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Incoterm
    form_class = IncotermForm
    template_name = "incoterm/incoterm_form.html"
    success_message = "Incoterm %(code)s mis à jour."
 
    def get_success_url(self):
        return reverse_lazy("facturation:incoterm_detail", kwargs={"pk": self.object.pk})
 
 
class IncotermDeleteView(LoginRequiredMixin, DeleteView):
    """Refuse la suppression tant que des factures utilisent l'incoterm."""
    model = Incoterm
    template_name = "incoterm/incoterm_confirm_delete.html"
    success_url = reverse_lazy("facturation:incoterm_liste")
 
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nb_factures"] = Facture.objects.filter(incoterm=self.object).count()
        return ctx
 
    def form_valid(self, form):
        if Facture.objects.filter(incoterm=self.object).exists():
            messages.error(self.request, "Suppression impossible : des factures utilisent cet incoterm.")
            return redirect("facturation:incoterm_detail", pk=self.object.pk)
        messages.success(self.request, f"Incoterm {self.object.code} supprimé.")
        return super().form_valid(form)
 