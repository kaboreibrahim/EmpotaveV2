from django import forms
from django.db.models import Q
from django.views.generic import ListView

from apps.documents.models import Document, TypeDocument

from .mixins import ClientRequiredMixin

INPUT_CLASS = (
    'bg-surface-container-low border border-outline-variant rounded-lg px-3 py-2 '
    'text-body-sm focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all'
)

# Rendu visuel (icône + couleur + libellé) de chaque statut, y compris l'état
# virtuel "aucun document déposé" (clé None) qui ne correspond à aucune ligne
# en base — seul un TypeDocument sans Document associé pour ce dossier.
STATUT_META = {
    None: {
        'label': 'Non ajouté', 'icone': 'schedule',
        'classes': 'bg-surface-container-high text-on-surface-variant',
    },
    'ajoute': {
        'label': 'Ajouté', 'icone': 'upload_file',
        'classes': 'bg-secondary/10 text-secondary',
    },
    'en_attente_validation': {
        'label': 'En attente de validation', 'icone': 'hourglass_empty',
        'classes': 'bg-tertiary/10 text-tertiary',
    },
    'valide': {
        'label': 'Validé', 'icone': 'check_circle',
        'classes': 'bg-primary/10 text-primary',
    },
    'rejete': {
        'label': 'Rejeté', 'icone': 'cancel',
        'classes': 'bg-error/10 text-error',
    },
}


def _ligne_document(type_document, document):
    return {
        'type_document': type_document,
        'document': document,
        'statut_meta': STATUT_META[document.statut if document else None],
    }


def construire_lignes_documents(dossier):
    """Une ligne par TypeDocument existant, avec son Document (ou None) pour ce
    dossier — garantit que tous les documents requis apparaissent, déposés ou non.
    Lecture seule : le client consulte l'état de ses documents, sans pouvoir les modifier.
    """
    documents_existants = {
        d.type_document_id: d
        for d in Document.objects.filter(dossier=dossier).select_related('type_document')
    }
    lignes = [
        _ligne_document(type_doc, documents_existants.get(type_doc.Id_TypeDocument))
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


class DocumentListeView(ClientRequiredMixin, ListView):
    """Documents rattachés aux dossiers du client connecté (lecture seule)."""
    model = Document
    template_name = 'DashboardClient/document/liste.html'
    context_object_name = 'document_list'
    paginate_by = 15

    def get_filter_form(self):
        if not hasattr(self, '_filter_form'):
            self._filter_form = FiltreDocumentForm(self.request.GET or None)
        return self._filter_form

    def get_base_queryset(self):
        return Document.objects.select_related('dossier', 'type_document').filter(
            dossier__id_client__user=self.request.user
        ).order_by('-date_created')

    def get_queryset(self):
        queryset = self.get_base_queryset()
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

        base = self.get_base_queryset()
        context['total_documents'] = base.count()
        context['documents_en_attente'] = base.filter(statut__in=['ajoute', 'en_attente_validation']).count()
        context['documents_termines'] = base.filter(statut='valide').count()

        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context
