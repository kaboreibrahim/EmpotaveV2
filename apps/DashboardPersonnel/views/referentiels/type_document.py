from django import forms
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.documents.models import Document, TypeDocument

from ..mixins import DeleteMessageMixin, FormMessageMixin

INPUT_CLASS = 'custom-input px-4 py-3 bg-surface-container-lowest text-body-md font-body-md'


class TypeDocumentForm(forms.ModelForm):
    class Meta:
        model = TypeDocument
        fields = ['type_document']
        widgets = {
            'type_document': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': "ex. Facture Commerciale, Certificat d'Origine"}),
        }
        labels = {'type_document': 'Nom du type de document'}


class FiltreTypeDocumentForm(forms.Form):
    q = forms.CharField(
        label='',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Rechercher un type de document...',
            'class': 'w-full pl-10 pr-4 py-2 bg-surface-container-low border border-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all font-body-sm text-body-sm rounded-lg',
        }),
    )


class ListeTypeDocument(ListView):
    """Référentiel des types de documents attendus (facture, packing list, certificat...)."""
    model = TypeDocument
    template_name = 'DashboardPersonnel/pages/type_document/liste.html'
    context_object_name = 'type_document_list'
    paginate_by = 15

    def get_filter_form(self):
        if not hasattr(self, '_filter_form'):
            self._filter_form = FiltreTypeDocumentForm(self.request.GET or None)
        return self._filter_form

    def get_queryset(self):
        queryset = TypeDocument.objects.annotate(
            nb_documents=Count('documents')
        ).order_by('type_document')
        form = self.get_filter_form()
        filters = form.cleaned_data if form.is_valid() else {}

        q = filters.get('q', '').strip()
        if q:
            queryset = queryset.filter(Q(type_document__icontains=q))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtre_form'] = self.get_filter_form()
        context['total_types'] = TypeDocument.objects.count()
        context['total_documents'] = Document.objects.count()

        params = self.request.GET.copy()
        params.pop('page', None)
        context['querystring'] = params.urlencode()
        return context


class CreerTypeDocument(FormMessageMixin, CreateView):
    model = TypeDocument
    form_class = TypeDocumentForm
    template_name = 'DashboardPersonnel/pages/type_document/create.html'
    success_url = reverse_lazy('DashboardPersonnel:type-document-liste')
    success_message = "Le type de document « %(type_document)s » a été ajouté avec succès."


class ModifierTypeDocument(FormMessageMixin, UpdateView):
    model = TypeDocument
    form_class = TypeDocumentForm
    template_name = 'DashboardPersonnel/pages/type_document/edit.html'
    success_url = reverse_lazy('DashboardPersonnel:type-document-liste')
    success_message = "Le type de document « %(type_document)s » a été modifié avec succès."


class DeleteTypeDocument(DeleteMessageMixin, DeleteView):
    model = TypeDocument
    template_name = 'DashboardPersonnel/pages/type_document/delete.html'
    success_url = reverse_lazy('DashboardPersonnel:type-document-liste')
    success_message = "Le type de document « %(object)s » a été supprimé avec succès."
