from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.DashboardPersonnel.forms import BanqueForm
from apps.referentiels.models import Banque

# `facture_set` = lien inverse Facture.banque -> Banque (nom Django par défaut)


class BanqueListView(LoginRequiredMixin, ListView):
    model = Banque
    template_name = "DashboardPersonnel/pages/banque/liste.html"
    context_object_name = "banques"
    paginate_by = 25

    def get_queryset(self):
        qs = Banque.objects.annotate(
            nb_factures=Count("facture", filter=Q(facture__deleted__isnull=True), distinct=True)
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(nom__icontains=q) | Q(titulaire__icontains=q)
                | Q(numero_compte__icontains=q) | Q(iban__icontains=q)
            )
        statut = self.request.GET.get("statut", "")
        if statut == "actives":
            qs = qs.filter(actif=True)
        elif statut == "inactives":
            qs = qs.filter(actif=False)
        return qs.order_by("nom")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["statut"] = self.request.GET.get("statut", "")
        return ctx


class BanqueDetailView(LoginRequiredMixin, DetailView):
    model = Banque
    template_name = "DashboardPersonnel/pages/banque/detail.html"
    context_object_name = "banque"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        factures = self.object.facture_set.select_related("client")
        ctx["nb_factures"] = factures.count()
        ctx["factures"] = factures[:10]
        return ctx


class BanqueCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Banque
    form_class = BanqueForm
    template_name = "DashboardPersonnel/pages/banque/form.html"
    success_message = "Banque %(nom)s enregistrée."

    def get_success_url(self):
        return reverse_lazy("DashboardPersonnel:detail", kwargs={"pk": self.object.pk})


class BanqueUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Banque
    form_class = BanqueForm
    template_name = "DashboardPersonnel/pages/banque/form.html"
    success_message = "Banque %(nom)s mise à jour."

    def get_success_url(self):
        return reverse_lazy("DashboardPersonnel:detail", kwargs={"pk": self.object.pk})


class BanqueToggleActifView(LoginRequiredMixin, View):
    """Active / désactive une banque (POST uniquement)."""
    http_method_names = ["post"]

    def post(self, request, pk):
        banque = get_object_or_404(Banque, pk=pk)
        banque.actif = not banque.actif
        banque.save(update_fields=["actif"])
        etat = "activée" if banque.actif else "désactivée"
        messages.success(request, f"Banque {banque.nom} {etat}.")
        return redirect("DashboardPersonnel:detail", pk=pk)


class BanqueDeleteView(LoginRequiredMixin, DeleteView):
    """Refuse la suppression tant que des factures utilisent la banque."""
    model = Banque
    template_name = "DashboardPersonnel/pages/banque/delete.html"
    success_url = reverse_lazy("DashboardPersonnel:banque-liste")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["nb_factures"] = self.object.facture_set.count()
        return ctx

    def form_valid(self, form):
        if self.object.facture_set.exists():
            messages.error(self.request, "Suppression impossible : des factures utilisent cette banque.")
            return redirect("DashboardPersonnel:detail", pk=self.object.pk)
        messages.success(self.request, f"Banque {self.object.nom} supprimée.")
        return super().form_valid(form)