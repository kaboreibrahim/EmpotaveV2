"""
apps/DashboardAgentSelection/forms.py
Formulaires de saisie des conteneurs par l'agent de sélection.
"""
from django import forms

from apps.conteneurs.models import Flexitanks, ISOTanks

# Photos obligatoires pour qu'un conteneur soit considéré comme sélectionné.
# Partagé avec views/rapport.py pour verrouiller la soumission du dossier tant
# qu'elles ne sont pas toutes fournies.
PHOTOS_OBLIGATOIRES = [
    'photo_devant',
    'photo_derriere',
    'photo_interieur',
    'photo_lateral_droit',
    'photo_lateral_gauche',
]

TEXT_INPUT_CLASSES = 'w-full bg-white border border-outline rounded p-3 text-body-md form-focus-ring'
SELECT_CLASSES = 'w-full bg-white border border-outline rounded p-3 text-body-md form-focus-ring'
FILE_INPUT_CLASSES = (
    'w-full text-body-sm text-on-surface-variant file:mr-4 file:py-2 file:px-4 '
    'file:rounded file:border-0 file:bg-primary-fixed file:text-on-primary-fixed '
    'file:font-label-md file:text-label-md hover:file:brightness-95'
)

# Champs communs à tout conteneur (ISO Tank ou Flexitank), portés par le
# mixin abstrait ConteneurCommunMixin — partagés entre les deux formulaires
# pour ne pas dupliquer deux fois les mêmes widgets.
CONTENEUR_COMMON_FIELDS = [
    'reference', 'etat',
    'photo_devant', 'photo_derriere', 'photo_interieur',
    'photo_lateral_droit', 'photo_lateral_gauche',
]
CONTENEUR_COMMON_WIDGETS = {
    'reference': forms.TextInput(attrs={'class': TEXT_INPUT_CLASSES, 'placeholder': 'MSKU 1234567'}),
    'etat': forms.Select(attrs={'class': SELECT_CLASSES}),
    'photo_devant': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
    'photo_derriere': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
    'photo_interieur': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
    'photo_lateral_droit': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
    'photo_lateral_gauche': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
}


class _ConteneurSelectionFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reference'].required = True
        self.fields['etat'].required = True
        for champ in PHOTOS_OBLIGATOIRES:
            self.fields[champ].required = True


class ISOTankSelectionForm(_ConteneurSelectionFormMixin, forms.ModelForm):
    """Fiche de sélection d'un ISO Tank."""

    class Meta:
        model = ISOTanks
        fields = CONTENEUR_COMMON_FIELDS
        widgets = CONTENEUR_COMMON_WIDGETS


class FlexitankSelectionForm(_ConteneurSelectionFormMixin, forms.ModelForm):
    """Fiche de sélection d'un Flexitank."""

    class Meta:
        model = Flexitanks
        fields = CONTENEUR_COMMON_FIELDS
        widgets = CONTENEUR_COMMON_WIDGETS
