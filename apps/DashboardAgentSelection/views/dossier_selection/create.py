from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.conteneurs.models import Dossier
from apps.DashboardAgentSelection.forms import (
    FlexitankSelectionForm,
    ISOTankSelectionForm,
)
from apps.notification.services import notifier

CREATE_TEMPLATE = 'DashboardAgentSelection/dossier/create.html'

# Statuts pendant lesquels un agent de sélection peut encore ajouter des conteneurs.
STATUTS_OUVERTS_A_LA_SELECTION = ('en_attente', 'selection_en_cours')


def _dossier_ouvert_a_la_selection(request, dossier_id):
    """Récupère le dossier, attribué à l'agent connecté et encore ouvert à l'ajout de conteneurs."""
    qs = Dossier.objects.select_related('Id_Pays')
    if not request.user.is_superuser:
        qs = qs.filter(Id_Agent_selection__user=request.user)
    dossier = get_object_or_404(qs, id=dossier_id)
    if dossier.statut not in STATUTS_OUVERTS_A_LA_SELECTION:
        raise Http404("Ce dossier n'est plus ouvert à l'ajout de conteneurs.")
    return dossier


@login_required
def ajouter_conteneur(request, dossier_id):
    """Ajoute un conteneur à un dossier.

    Le type de dossier détermine la nature du conteneur ajouté :
    ISO_20_pieds -> ISO Tank, tout autre type -> Flexitank. Dans les deux cas,
    la référence, l'état et les 5 photos obligatoires (communes aux deux
    modèles) restent requis : ce sont elles, avec la date de sélection, qui
    conditionnent la soumission du dossier (voir views/rapport.py).
    """
    dossier = _dossier_ouvert_a_la_selection(request, dossier_id)
    est_iso = dossier.type_conteneur == 'ISO_20_pieds'
    FormClass = ISOTankSelectionForm if est_iso else FlexitankSelectionForm

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES)

        if form.is_valid():
            conteneur = form.save(commit=False)
            conteneur.dossier = dossier
            conteneur.save()

            demarrage = dossier.statut == 'en_attente'
            dossier.demarrer_selection()  # en_attente -> selection_en_cours + date_de_selection
            if demarrage:
                notifier(
                    dossier.id_client.user,
                    f"La sélection des conteneurs a démarré pour votre dossier {dossier.TRD} — {dossier.projet}.",
                )

            messages.success(request, f"Conteneur {conteneur.reference} ajouté au dossier {dossier.projet}.")
            return redirect('DashboardAgentSelection:dossier-detail', dossier_id=dossier.id)
    else:
        form = FormClass()

    return render(request, CREATE_TEMPLATE, {
        'dossier': dossier,
        'form': form,
        'est_iso': est_iso,
    })
