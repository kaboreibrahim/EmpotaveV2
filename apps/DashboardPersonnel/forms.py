from django import forms

from apps.referentiels.models import Banque

CHAMP = (
    "w-full rounded-lg border border-outline-variant bg-surface-container-lowest "
    "px-3 py-2 text-body-md text-on-surface focus:border-primary "
    "focus:outline-none focus:ring-1 focus:ring-primary"
)


class BanqueForm(forms.ModelForm):
    class Meta:
        model = Banque
        fields = ["nom", "titulaire", "numero_compte", "iban", "bic_swift", "actif"]
        labels = {
            "nom": "Banque",
            "titulaire": "Nom du propriétaire du compte",
            "numero_compte": "Numéro de compte",
            "iban": "Code IBAN",
            "bic_swift": "Code BIC/SWIFT",
            "actif": "Banque active (proposée dans le formulaire de facture)",
        }
        help_texts = {"iban": "Tel qu'il doit apparaître sur la facture."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nom, champ in self.fields.items():
            if nom == "actif":
                champ.widget.attrs["class"] = "h-5 w-5 rounded border-outline-variant text-primary focus:ring-primary"
            else:
                champ.widget.attrs["class"] = CHAMP

    def clean_nom(self):
        return self.cleaned_data["nom"].strip().upper()

    def clean_titulaire(self):
        return self.cleaned_data["titulaire"].strip().upper()

    def clean_iban(self):
        return self.cleaned_data["iban"].strip().upper()

    def clean_bic_swift(self):
        return self.cleaned_data["bic_swift"].strip().upper()