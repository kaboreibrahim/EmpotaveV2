from django.urls import path

from apps.facturation.views.facture import FactureListView, FactureCreateView, FactureDetailView, FactureUpdateView, FactureDeleteView, facture_pdf, envoyer_facture_email, valider_facture
from apps.facturation.views.icoterm import IncotermListView, IncotermCreateView, IncotermDetailView, IncotermUpdateView, IncotermDeleteView

app_name = "facturation"

urlpatterns = [
    path("", FactureListView.as_view(), name="liste"),
    path("nouvelle/", FactureCreateView.as_view(), name="creer"),
    path("<uuid:pk>/", FactureDetailView.as_view(), name="detail"),
    path("<uuid:pk>/modifier/", FactureUpdateView.as_view(), name="modifier"),
    path("<uuid:pk>/supprimer/", FactureDeleteView.as_view(), name="supprimer"),
    path("<uuid:pk>/valider/", valider_facture, name="valider"),
    path("<uuid:pk>/pdf/", facture_pdf, name="pdf"),
    path("<uuid:pk>/envoyer-email/", envoyer_facture_email, name="envoyer_email"),

    # Incoterms
    path("incoterms/", IncotermListView.as_view(), name="incoterm_liste"),
    path("incoterms/nouveau/", IncotermCreateView.as_view(), name="incoterm_creer"),
    path("incoterms/<uuid:pk>/", IncotermDetailView.as_view(), name="incoterm_detail"),
    path("incoterms/<uuid:pk>/modifier/", IncotermUpdateView.as_view(), name="incoterm_modifier"),
    path("incoterms/<uuid:pk>/supprimer/", IncotermDeleteView.as_view(), name="incoterm_supprimer"),
]