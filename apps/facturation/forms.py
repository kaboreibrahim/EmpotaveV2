from django import forms
from django.forms import inlineformset_factory

from .models import Facture, LigneFacture, Incoterm

# Classes Tailwind (si build Tailwind : ajouter apps/**/forms.py aux chemins `content`)
CHAMP = (
    "w-full rounded-lg border border-outline-variant bg-surface-container-lowest "
    "px-3 py-2 text-body-md text-on-surface focus:border-primary "
    "focus:outline-none focus:ring-1 focus:ring-primary"
)


class FactureForm(forms.ModelForm):
    class Meta:
        model = Facture
        fields = [
            "ref_client", "client", "date_facturation", "banque", "conditions_reglement",
            "incoterm", "quantite_unites", "conditionnement", "produit", "usine",
            "port_livraison", "destination", "pu_fcfa_unite", "ref_dossier", "taux_change",
        ]
        labels = {
            "ref_client": "Réf. client (TR)",
            "client": "Client (adressé à)",
            "date_facturation": "Date de facturation",
            "banque": "Banque (pied de facture)",
            "conditions_reglement": "Conditions de règlement",
            "incoterm": "Incoterm",
            "quantite_unites": "Quantité",
            "conditionnement": "Conditionnement",
            "produit": "Produit",
            "usine": "Usine d'origine",
            "port_livraison": "Port de chargement (POL)",
            "destination": "Destination (POD)",
            "pu_fcfa_unite": "Prix unitaire (FCFA)",
            "ref_dossier": "Réf. dossier",
            "taux_change": "Taux FCFA pour 1 EUR",
        }
        widgets = {
            "date_facturation": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.widget.attrs["class"] = CHAMP
        self.fields["banque"].queryset = self.fields["banque"].queryset.filter(actif=True)


class LigneFactureForm(forms.ModelForm):
    class Meta:
        model = LigneFacture
        fields = ["designation", "tva_taux", "pu_ht", "quantite"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.widget.attrs["class"] = CHAMP
        self.fields["quantite"].widget.attrs["step"] = "0.01"
        self.fields["tva_taux"].widget.attrs["step"] = "0.01"


LigneFactureFormSet = inlineformset_factory(
    Facture, LigneFacture, form=LigneFactureForm,
    extra=1, can_delete=True, min_num=1, validate_min=True,
)


class IncotermForm(forms.ModelForm):
    class Meta:
        model = Incoterm
        fields = ["code", "libelle"]
        labels = {"code": "Code", "libelle": "Libellé"}
        help_texts = {"code": "3 lettres, ex. FOB, CIF, CFR.", "libelle": "Ex. FOB - Free On Board"}
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.widget.attrs["class"] = CHAMP
 
    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        # all_objects inclut les incoterms supprimés (soft delete) : l'unicité en base les compte
        if Incoterm.all_objects.filter(code=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ce code existe déjà (éventuellement dans les éléments supprimés).")
        return code