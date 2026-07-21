from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.core.exceptions import ValidationError
from typing import Dict, Type, Tuple, Optional
from django.db.models import Model
from django.forms import ModelForm
from django.utils.timezone import now
from django.utils.text import slugify
from conteneurs.forms import *
# managers.py
from django.core.exceptions import ValidationError
from typing import Dict, Type, Tuple, Optional
from django.db.models import Model
from django.forms import ModelForm
from django.utils.text import slugify

class DocumentManager:
    """Gestionnaire centralisé pour la manipulation des documents"""
    
    # Mapping des types de documents vers leurs formulaires et modèles respectifs
    DOCUMENT_MAPPING: Dict[str, Tuple[Type[ModelForm], Type[Model]]] = {
        "Facture Commerciale": (FactureCommercialForm, FactureCommerciale),
        "Packing List": (PackingListForm, PackingList),
        "Certificat d'Origine": (CertificatOrigineForm, CertificatOrigine),
        "Confirmation du Booking": (ConfirmationBookingForm, ConfirmationBooking),
        "Certificat Phytosanitaire": (CertificatPhytosanitaireForm, CertificatPhytosanitaire),
        "Copies des BLS": (CopiesBLSForm, CopiesBLS),
        "Rapport d'Empotage": (RapportEmpotageForm, RapportEmpotage),
        "Rapport de Sélection": (RapportSelectionForm, RapportSelection),
        "Autorisation d'Exportation": (AutorisationExploitationForm, AutorisationExploitation),
        "EC": (ECForm, EC),
        "COA": (COAForm, COA),
        "Declaration": (DeclarationForm, Declaration),
        "IER D'ENTRE": (IER_ENTREForm, IER_ENTRE),
        "IER DE SORTIE": (IER_SORTIEForm, IER_SORTIE),
    }

    @classmethod
    def get_all_documents(cls, dossier: 'Dossier') -> Dict[str, Optional[Model]]:
        """Récupère tous les documents associés à un dossier."""
        return {
            type_doc: modele.objects.filter(dossier=dossier).first()
            for type_doc, (_, modele) in cls.DOCUMENT_MAPPING.items()
        }

    @classmethod
    def get_form_and_model(cls, type_document: str) -> Tuple[Type[ModelForm], Type[Model]]:
        """Récupère les classes de formulaire et de modèle pour un type de document donné."""
        if type_document not in cls.DOCUMENT_MAPPING:
            raise ValidationError(f"Type de document non pris en charge: {type_document}")
        return cls.DOCUMENT_MAPPING[type_document]

    @classmethod
    def get_original_document_type(cls, slugified_type: str) -> Optional[str]:
        """Convertit un type de document slugifié en son format original."""
        type_document_map = {
            slugify(key): key for key in cls.DOCUMENT_MAPPING.keys()
        }
        return type_document_map.get(slugify(slugified_type))

# views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.timezone import now

def suivi_document(request, pk: int):
    """Vue pour suivre l'état des documents d'un dossier."""
    dossier = get_object_or_404(Dossier, pk=pk)
    documents = DocumentManager.get_all_documents(dossier)
    
    total_docs = len(documents)
    completed_docs = sum(1 for doc in documents.values() if doc is not None and doc.fichier)
    completion_percentage = float(completed_docs) / total_docs * 100 if total_docs > 0 else 0
    
    status_counts = {
        'complete': completed_docs,
        'missing': sum(1 for doc in documents.values() if doc is None),
        'pending': sum(1 for doc in documents.values() if doc is not None and not doc.fichier)
    }
    
    return render(request, 'pages/documents/suivi_document.html', {
        'dossier': dossier,
        'documents': documents,
        'total_docs': total_docs,
        'completed_docs': completed_docs,
        'completion_percentage': completion_percentage,
        'status_counts': status_counts,
    })

def ajouter_document(request, pk: int, type_document: str):
    """Vue pour ajouter un nouveau document à un dossier."""
    # Récupérer le type de document original à partir du slug
    original_type_document = DocumentManager.get_original_document_type(type_document)
    
    if not original_type_document:
        messages.error(request, f"Type de document non reconnu: {type_document}")
        return redirect('suivi_document', pk=pk)
        
    dossier = get_object_or_404(Dossier, pk=pk)
    user = request.user
    
    try:
        form_class, model_class = DocumentManager.get_form_and_model(original_type_document)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect('suivi_document', pk=dossier.pk)

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            # Supprimer l'ancien document s'il existe
            ancien_document = model_class.objects.filter(dossier=dossier).first()
            if ancien_document:
                ancien_document.fichier.delete(save=False)
                ancien_document.delete()

            # Ajouter le nouveau document
            document = form.save(commit=False)
            document.dossier = dossier
            document.date_modification = now()
            document.save()

            # Envoyer un email avec les détails
            subject = f"Nouveau document ajouté au dossier {dossier.TRD}"
            message = (
                f"Bonjour,\n\n"
                f"Un nouveau document a été ajouté au dossier {dossier.TRD}:\n"
                f"- Nom du fichier : {document.type_document}\n"
                f"- De l'utilisateur  : {user}\n"
                f"- Nom du Projet : {dossier.projet}\n\n"
                f"Vous pouvez consulter les détails ici : "
                f"https://empotage-oils-of-africa.net\n"
                f"Cordialement,\nL'équipe operationelle"
            )
            send_mail(
                subject,
                message,
                'empotageoilsofafrica@gmail.com',
                [
                    user.email,
                    'ops@oils-of-africa.ci',
                    'trading@oils-of-africa.ci',
                    'appro.stock@oils-of-africa.ci',
                    'alice.tuo@oils-of-africa.ci',
                   
                ]
            )

            messages.success(request, f"{original_type_document} ajouté avec succès !")
            return redirect('suivi_document', pk=dossier.pk)
    else:
        form = form_class()

    return render(request, 'pages/documents/ajouter_document.html', {
        'form': form,
        'dossier': dossier,
        'type_document': original_type_document,
    })