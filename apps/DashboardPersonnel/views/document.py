from django import forms
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from apps.conteneurs.models import Dossier
from apps.documents.models import Document, TypeDocument
from apps.notification.services import NotificationService

from .mixins import ActionPermissionRequiredMixin, FormMessageMixin, ModulePermissionRequiredMixin

INPUT_CLASS = (
    'bg-surface-container-low border border-outline-variant rounded-lg px-3 py-2 '
    'text-body-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all'
)
CUSTOM_INPUT_CLASS = 'custom-input px-4 py-3'

ROW_TEMPLATE = 'DashboardPersonnel/pages/document/_document_row.html'

# Rendu visuel (icône + couleur + libellé) de chaque statut, y compris l'état
# virtuel "aucun document déposé" (clé None) qui ne correspond à aucune ligne
# en base — seul un TypeDocument sans Document associé pour ce dossier.
STATUT_META = {
    None: {
        'valeur': '', 'label': 'Non ajouté', 'icone': 'schedule',
        'classes': 'bg-surface-container-high text-on-surface-variant',
    },
    'ajoute': {
        'valeur': 'ajoute', 'label': 'Ajouté', 'icone': 'upload_file',
        'classes': 'bg-secondary/10 text-secondary',
    },
    'en_attente_validation': {
        'valeur': 'en_attente_validation', 'label': 'En attente de validation', 'icone': 'hourglass_empty',
        'classes': 'bg-tertiary/10 text-tertiary',
    },
    'valide': {
        'valeur': 'valide', 'label': 'Validé', 'icone': 'check_circle',
        'classes': 'bg-primary/10 text-primary',
    },
    'rejete': {
        'valeur': 'rejete', 'label': 'Rejeté', 'icone': 'cancel',
        'classes': 'bg-error/10 text-error',
    },
}


def _ligne_document(dossier, type_document, document):
    return {
        'dossier': dossier,
        'type_document': type_document,
        'document': document,
        'statut_meta': STATUT_META[document.statut if document else None],
    }


def construire_lignes_documents(dossier):
    """Une ligne par TypeDocument existant, avec son Document (ou None) pour ce
    dossier — garantit que tous les documents requis apparaissent, déposés ou non.
    """
    documents_existants = {
        d.type_document_id: d
        for d in Document.objects.filter(dossier=dossier).select_related('type_document', 'ajoute_par')
    }
    lignes = [
        _ligne_document(dossier, type_doc, documents_existants.get(type_doc.Id_TypeDocument))
        for type_doc in TypeDocument.objects.order_by('type_document')
    ]
    total_requis = len(lignes)
    total_ajoutes = sum(1 for ligne in lignes if ligne['document'] is not None)
    progression_pct = round(total_ajoutes / total_requis * 100) if total_requis else 0
    return {
        'lignes_documents': lignes,
        'documents_total_requis': total_requis,
        'documents_total_ajoutes': total_ajoutes,
        'documents_progression_pct': progression_pct,
    }


def _progression_json(dossier):
    total_requis = TypeDocument.objects.count()
    total_ajoutes = Document.objects.filter(dossier=dossier).count()
    progression_pct = round(total_ajoutes / total_requis * 100) if total_requis else 0
    return {
        'total_requis': total_requis,
        'total_ajoutes': total_ajoutes,
        'progression_pct': progression_pct,
        'texte': f"{total_ajoutes} document{'s' if total_ajoutes != 1 else ''} sur {total_requis} "
                 f"{'ont' if total_ajoutes != 1 else 'a'} été ajouté{'s' if total_ajoutes != 1 else ''}.",
    }


def _row_response(dossier, type_document, document):
    ligne = _ligne_document(dossier, type_document, document)
    row_html = render_to_string(ROW_TEMPLATE, {'ligne': ligne})
    return JsonResponse({
        'success': True,
        'row_html': row_html,
        'type_document_id': str(type_document.Id_TypeDocument),
        'progression': _progression_json(dossier),
    })


class FiltreDocumentForm(forms.Form):
    q = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Recherche (TRD, projet, type de document...)',
            'class': 'w-full pl-10 pr-4 py-2 bg-surface-container-low border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all font-body-sm text-body-sm rounded-lg',
        }),
    )
    filtre_type_document = forms.ChoiceField(
        label='', required=False,
        widget=forms.Select(attrs={'class': INPUT_CLASS}),
    )
    filtre_statut = forms.ChoiceField(label='', required=False, widget=forms.Select(attrs={'class': INPUT_CLASS}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type_choices = TypeDocument.objects.order_by('type_document').values_list('Id_TypeDocument', 'type_document')
        self.fields['filtre_type_document'].choices = [('', 'Tous les types')] + list(type_choices)
        self.fields['filtre_statut'].choices = [('', 'Tous les statuts'), *Document.STATUT_CHOICES]


class DocumentListeView(ModulePermissionRequiredMixin, ListView):
    """Gestion documentaire : liste de tous les documents rattachés aux dossiers."""
    model = Document
    template_name = 'DashboardPersonnel/pages/document/liste.html'
    context_object_name = 'document_list'
    paginate_by = 15

    def get_filter_form(self):
        if not hasattr(self, '_filter_form'):
            self._filter_form = FiltreDocumentForm(self.request.GET or None)
        return self._filter_form

    def get_queryset(self):
        queryset = Document.objects.select_related('dossier', 'type_document').order_by('-date_created')
        form = self.get_filter_form()
        filters = form.cleaned_data if form.is_valid() else {}

        q = filters.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(dossier__TRD__icontains=q)
                | Q(dossier__projet__icontains=q)
                | Q(type_document__type_document__icontains=q)
            )

        filtre_type_document = filters.get('filtre_type_document', '').strip()
        if filtre_type_document:
            queryset = queryset.filter(type_document_id=filtre_type_document)

        filtre_statut = filters.get('filtre_statut', '').strip()
        if filtre_statut:
            queryset = queryset.filter(statut=filtre_statut)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtre_form'] = self.get_filter_form()
        context['total_documents'] = Document.objects.count()
        context['documents_en_attente'] = Document.objects.filter(
            statut__in=['ajoute', 'en_attente_validation']
        ).count()
        context['documents_termines'] = Document.objects.filter(statut='valide').count()

        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class DocumentForm(forms.ModelForm):
    """Le statut n'est pas saisi : un document nouvellement déposé démarre
    toujours au statut "Ajouté" (voir Document.statut, valeur par défaut) et
    attend une validation ultérieure par le personnel.
    """

    class Meta:
        model = Document
        fields = ['dossier', 'type_document', 'fichier']
        widgets = {
            'dossier': forms.Select(attrs={'class': CUSTOM_INPUT_CLASS}),
            'type_document': forms.Select(attrs={'class': CUSTOM_INPUT_CLASS}),
            'fichier': forms.ClearableFileInput(attrs={'class': 'block w-full text-body-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dossier'].queryset = Dossier.objects.order_by('-date_created')
        self.fields['dossier'].label_from_instance = lambda d: f"{d.TRD} — {d.projet}"
        self.fields['type_document'].queryset = TypeDocument.objects.order_by('type_document')

    def clean(self):
        cleaned_data = super().clean()
        dossier = cleaned_data.get('dossier')
        type_document = cleaned_data.get('type_document')
        if dossier and type_document:
            doublon = Document.objects.filter(dossier=dossier, type_document=type_document)
            if self.instance.pk:
                doublon = doublon.exclude(pk=self.instance.pk)
            if doublon.exists():
                raise forms.ValidationError(
                    f"Un document de type « {type_document} » a déjà été ajouté pour ce dossier."
                )
        return cleaned_data


class DocumentCreateView(ModulePermissionRequiredMixin, FormMessageMixin, CreateView):
    """Ajout d'un document rattaché à un dossier (formulaire pleine page)."""
    model = Document
    form_class = DocumentForm
    template_name = 'DashboardPersonnel/pages/document/create.html'
    success_url = reverse_lazy('DashboardPersonnel:document-liste')
    success_message = "Le document a été ajouté avec succès."

    def get_initial(self):
        initial = super().get_initial()
        dossier_id = self.request.GET.get('dossier')
        if dossier_id:
            initial['dossier'] = dossier_id
        return initial

    def form_valid(self, form):
        form.instance.ajoute_par = self.request.user
        return super().form_valid(form)


# =============================================================================
# Actions AJAX depuis la matrice "Documents" de l'écran détail dossier :
# ajouter / remplacer / supprimer / changer le statut, sans recharger la page.
# Chaque vue retourne le HTML de la ligne concernée + la progression globale.
# =============================================================================

class DocumentAjouterAjaxView(ActionPermissionRequiredMixin, View):
    """Dépose le fichier d'un type de document encore manquant pour un dossier."""
    permission_model = Document
    permission_action = 'add'

    def post(self, request, dossier_id, type_document_id):
        dossier = get_object_or_404(Dossier, pk=dossier_id)
        type_document = get_object_or_404(TypeDocument, pk=type_document_id)
        fichier = request.FILES.get('fichier')

        if not fichier:
            return JsonResponse({'success': False, 'error': "Aucun fichier fourni."}, status=400)
        if Document.objects.filter(dossier=dossier, type_document=type_document).exists():
            return JsonResponse({'success': False, 'error': "Ce document a déjà été ajouté."}, status=400)

        document = Document.objects.create(
            dossier=dossier, type_document=type_document, fichier=fichier, ajoute_par=request.user,
        )
        NotificationService.notify_document_added(document)
        return _row_response(dossier, type_document, document)


class DocumentRemplacerAjaxView(ActionPermissionRequiredMixin, View):
    """Remplace le fichier d'un document existant ; repasse son statut à "Ajouté"
    puisqu'un nouveau fichier doit être revalidé."""
    permission_model = Document
    permission_action = 'change'

    def post(self, request, pk):
        document = get_object_or_404(Document.objects.select_related('dossier', 'type_document'), pk=pk)
        fichier = request.FILES.get('fichier')
        if not fichier:
            return JsonResponse({'success': False, 'error': "Aucun fichier fourni."}, status=400)

        document.fichier = fichier
        document.statut = 'ajoute'
        document.ajoute_par = request.user
        document.save(update_fields=['fichier', 'statut', 'ajoute_par', 'date_modifier'])
        return _row_response(document.dossier, document.type_document, document)


class DocumentSupprimerAjaxView(ActionPermissionRequiredMixin, View):
    """Supprime (soft-delete) un document ; la ligne repasse à l'état "Non ajouté"."""
    permission_model = Document
    permission_action = 'delete'

    def post(self, request, pk):
        document = get_object_or_404(Document.objects.select_related('dossier', 'type_document'), pk=pk)
        dossier, type_document = document.dossier, document.type_document
        document.delete()
        return _row_response(dossier, type_document, None)


class DocumentChangerStatutAjaxView(ActionPermissionRequiredMixin, View):
    """Change le statut de validation d'un document déjà déposé."""
    permission_model = Document
    permission_action = 'change'

    def post(self, request, pk):
        document = get_object_or_404(Document.objects.select_related('dossier', 'type_document'), pk=pk)
        statut = request.POST.get('statut')
        if statut not in dict(Document.STATUT_CHOICES):
            return JsonResponse({'success': False, 'error': "Statut invalide."}, status=400)

        document.statut = statut
        document.save(update_fields=['statut', 'date_modifier'])
        return _row_response(document.dossier, document.type_document, document)
