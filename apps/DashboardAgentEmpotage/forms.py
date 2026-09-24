"""
apps/DashboardAgentEmpotage/forms.py
Formulaires de saisie des conteneurs par l'agent d'empotage.
Contrairement à l'agent de sélection (qui crée le conteneur), l'agent
d'empotage complète un conteneur déjà créé avec les informations propres
à l'empotage : poids, température, photos de chargement et plombs.
"""
from decimal import Decimal

from django import forms

from apps.conteneurs.models import Flexitanks, ISOTanks

# Champs requis pour qu'un conteneur soit considéré comme empoté (alignés
# sur ConteneurCommunMixin.verifier_statut, partagé avec views/rapport.py
# pour verrouiller la soumission du dossier tant qu'ils ne sont pas remplis).
CHAMPS_OBLIGATOIRES = ['poids_net']

# Champs de poids dont la valeur par defaut en base (0.00) ne doit pas
# s'afficher comme une vraie saisie : le champ reste vide, avec "0.00" en
# placeholder, tant que l'agent n'a rien renseigne.
CHAMPS_POIDS_VIDES_SI_ZERO = ['poids_net', 'poids_equipements', 'poids_brute']

TEXT_INPUT_CLASSES = 'w-full bg-white border border-outline rounded p-3 text-body-md form-focus-ring'
NUMBER_INPUT_CLASSES = 'w-full bg-white border border-outline rounded p-3 text-body-md form-focus-ring'
FILE_INPUT_CLASSES = (
    'w-full text-body-sm text-on-surface-variant file:mr-4 file:py-2 file:px-4 '
    'file:rounded file:border-0 file:bg-primary-fixed file:text-on-primary-fixed '
    'file:font-label-md file:text-label-md hover:file:brightness-95'
)

# Champs communs à tout conteneur pour l'étape d'empotage — portés par le
# mixin abstrait ConteneurCommunMixin, partagés entre les deux formulaires.
CONTENEUR_COMMON_FIELDS = [
    'poids_net', 'Temerature',
    'photo_debut', 'photo_pendant', 'photo_fin',
]
CONTENEUR_COMMON_WIDGETS = {
    'poids_net':    forms.NumberInput(attrs={'class': NUMBER_INPUT_CLASSES, 'step': '0.01', 'placeholder': '0.00'}),
    'Temerature':   forms.NumberInput(attrs={'class': NUMBER_INPUT_CLASSES, 'step': '0.1', 'placeholder': '°C'}),
    'photo_debut':   forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
    'photo_pendant': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
    'photo_fin':     forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
}


class _ConteneurEmpotageFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in CHAMPS_OBLIGATOIRES:
            self.fields[champ].required = True
        for champ in CHAMPS_POIDS_VIDES_SI_ZERO:
            if champ in self.initial and self.initial[champ] in (0, Decimal('0.00'), None):
                self.initial[champ] = ''


class ISOTankEmpotageForm(_ConteneurEmpotageFormMixin, forms.ModelForm):
    """Complète l'empotage d'un ISO Tank : poids, température, photos, plombs."""

    class Meta:
        model = ISOTanks
        fields = CONTENEUR_COMMON_FIELDS + [
            'plombAmateur1', 'photoPlombAmateur1',
            'plombAmateur2', 'photoPlombAmateur2',
            'plombAmateur3', 'photoPlombAmateur3',
            'Plombs_oils1', 'photo_plombs_oils1',
            'Plombs_oils2', 'photo_plombs_oils2',
        ]
        widgets = {
            **CONTENEUR_COMMON_WIDGETS,
            'plombAmateur1': forms.TextInput(attrs={'class': TEXT_INPUT_CLASSES}),
            'plombAmateur2': forms.TextInput(attrs={'class': TEXT_INPUT_CLASSES}),
            'plombAmateur3': forms.TextInput(attrs={'class': TEXT_INPUT_CLASSES}),
            'photoPlombAmateur1': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
            'photoPlombAmateur2': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
            'photoPlombAmateur3': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
            'Plombs_oils1': forms.TextInput(attrs={'class': TEXT_INPUT_CLASSES}),
            'Plombs_oils2': forms.TextInput(attrs={'class': TEXT_INPUT_CLASSES}),
            'photo_plombs_oils1': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
            'photo_plombs_oils2': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
        }


class FlexitankEmpotageForm(_ConteneurEmpotageFormMixin, forms.ModelForm):
    """Complète l'empotage d'un Flexitank : poids, température, photos, plombs, heating pad."""

    def __init__(self, *args, choix_numero_flextank=None, choix_numero_heatingpad=None, **kwargs):
        """`choix_numero_flextank`/`choix_numero_heatingpad` (listes de numéros de
        série, ou None) viennent du brouillon oils-stock-api du dossier — voir
        views/dossier_empotage/create.py. Quand fournis, remplacent le champ
        texte libre par un select ; sinon (dossier non lié ou API injoignable),
        le champ reste un texte libre comme avant l'intégration."""
        super().__init__(*args, **kwargs)
        if choix_numero_flextank:
            self.fields['numeroFlextank'].widget = forms.Select(
                choices=[('', '---------')] + [(v, v) for v in choix_numero_flextank],
                attrs={'class': TEXT_INPUT_CLASSES},
            )
        if choix_numero_heatingpad:
            self.fields['Numeroheatingpad'].widget = forms.Select(
                choices=[('', '---------')] + [(v, v) for v in choix_numero_heatingpad],
                attrs={'class': TEXT_INPUT_CLASSES},
            )

    class Meta:
        model = Flexitanks
        fields = CONTENEUR_COMMON_FIELDS + [
            'poids_brute', 'poids_equipements',
            'numeroFlextank', 'photoFlextank',
            'Numeroheatingpad', 'Photoheatingpad',
            'plombs_amateur', 'plombs_amateur_photo',
            'Plombs_oils', 'photo_plombs_oils',
        ]
        widgets = {
            **CONTENEUR_COMMON_WIDGETS,
            'poids_brute':       forms.NumberInput(attrs={
                'class': NUMBER_INPUT_CLASSES + ' bg-surface-container-high cursor-not-allowed',
                'step': '0.01', 'readonly': 'readonly', 'tabindex': '-1', 'placeholder': '0.00',
            }),
            'poids_equipements': forms.NumberInput(attrs={'class': NUMBER_INPUT_CLASSES, 'step': '0.01', 'placeholder': '0.00'}),
            'numeroFlextank':    forms.TextInput(attrs={'class': TEXT_INPUT_CLASSES}),
            'photoFlextank':     forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
            'Numeroheatingpad':  forms.TextInput(attrs={'class': TEXT_INPUT_CLASSES}),
            'Photoheatingpad':   forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
            'plombs_amateur':       forms.TextInput(attrs={'class': TEXT_INPUT_CLASSES}),
            'plombs_amateur_photo': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
            'Plombs_oils':       forms.TextInput(attrs={'class': TEXT_INPUT_CLASSES}),
            'photo_plombs_oils': forms.ClearableFileInput(attrs={'class': FILE_INPUT_CLASSES}),
        }
