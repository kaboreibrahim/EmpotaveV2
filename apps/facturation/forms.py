from django import forms
from django.forms import inlineformset_factory

from .models import CHAMPS_HORS_EXW, OPTIONS_EXW, TEXTES_INCOTERM, UNITES, Facture, LigneFacture

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
        # Optionnels en base (vides en SS1 / SS2) mais obligatoires pour SS3 à SS5
        for nom in ("ref_client", "produit", "port_livraison", "destination"):
            self.fields[nom].required = self._incoterm() not in OPTIONS_EXW
        # lu par le JS du formulaire (aperçu du texte, champs masqués en SS1 / SS2)
        self.textes_incoterm = {
            "textes": {str(code): texte for code, texte in TEXTES_INCOTERM.items()},
            "unites": UNITES,
            "options_exw": [str(code) for code in OPTIONS_EXW],
            "champs_hors_exw": CHAMPS_HORS_EXW,
        }

    def _incoterm(self):
        if self.is_bound:
            return self.data.get(self.add_prefix("incoterm"))
        return self.initial.get("incoterm", self.instance.incoterm)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("incoterm") in OPTIONS_EXW:
            # départ entrepôt : on n'enregistre pas d'anciennes valeurs restées masquées
            for nom in CHAMPS_HORS_EXW:
                cleaned[nom] = "" if nom.startswith("ref_") else None
        return cleaned


class LigneFactureForm(forms.ModelForm):
    class Meta:
        model = LigneFacture
        fields = ["designation", "tva_taux", "pu_ht", "quantite", "ordre"]
        widgets = {"ordre": forms.HiddenInput()}  # renseigné par le JS du formulaire

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.widget.attrs["class"] = CHAMP
        self.fields["quantite"].widget.attrs["step"] = "0.01"
        self.fields["tva_taux"].widget.attrs["step"] = "0.01"
        self.fields["ordre"].required = False

    def clean_ordre(self):
        return self.cleaned_data.get("ordre") or 0

    def has_changed(self):
        # Une ligne vide ajoutée reçoit un ordre du JS : ce n'est pas une saisie,
        # sinon le formset exigerait la désignation sur une ligne laissée vide.
        if self.instance._state.adding:  # pk UUID déjà rempli : on teste "pas encore en base"
            return any(nom != "ordre" for nom in self.changed_data)
        return super().has_changed()


LigneFactureFormSet = inlineformset_factory(
    Facture, LigneFacture, form=LigneFactureForm,
    extra=1, can_delete=True, min_num=1, validate_min=True,
)

