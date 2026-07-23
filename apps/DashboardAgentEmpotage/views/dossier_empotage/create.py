from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.conteneurs.models import Flexitanks, ISOTanks
from apps.conteneurs.services import verifier_paiement
from apps.DashboardAgentEmpotage.forms import FlexitankEmpotageForm, ISOTankEmpotageForm

CREATE_TEMPLATE = 'DashboardAgentEmpotage/dossier_empotage/create.html'
SELECT_RELATED = ('dossier', 'dossier__Id_Pays')

# Statut du dossier pendant lequel l'agent d'empotage peut encore renseigner les conteneurs.
STATUTS_OUVERTS_A_L_EMPOTAGE = ('empotage_en_cours',)


def _conteneur_ouvert_a_l_empotage(request, pk):
    """Récupère le conteneur (ISO Tank ou Flexitank), attribué à l'agent connecté et
    dont le dossier est encore ouvert à la saisie d'empotage."""
    qs_iso = ISOTanks.objects.select_related(*SELECT_RELATED)
    qs_flexi = Flexitanks.objects.select_related(*SELECT_RELATED)
    if not request.user.is_superuser:
        qs_iso = qs_iso.filter(dossier__Id_Agent_empotage__user=request.user)
        qs_flexi = qs_flexi.filter(dossier__Id_Agent_empotage__user=request.user)

    conteneur = qs_iso.filter(pk=pk).first()
    est_iso = True
    if conteneur is None:
        conteneur = qs_flexi.filter(pk=pk).first()
        est_iso = False
    if conteneur is None:
        raise Http404("Conteneur introuvable ou non attribué à cet agent.")
    verifier_paiement(conteneur.dossier)
    if conteneur.dossier.statut not in STATUTS_OUVERTS_A_L_EMPOTAGE:
        raise Http404("Ce dossier n'est plus ouvert à la saisie d'empotage.")
    return conteneur, est_iso


@login_required
def renseigner_empotage(request, pk):
    """Complète l'empotage d'un conteneur : poids, température, photos et plombs.

    Le conteneur existe déjà (créé par l'agent de sélection) ; l'agent
    d'empotage vient uniquement en compléter les informations propres au
    chargement. Une fois le poids net renseigné, le conteneur passe au
    statut "empoté" (voir ConteneurCommunMixin.verifier_statut).
    """
    conteneur, est_iso = _conteneur_ouvert_a_l_empotage(request, pk)
    FormClass = ISOTankEmpotageForm if est_iso else FlexitankEmpotageForm

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=conteneur)

        if form.is_valid():
            conteneur = form.save(commit=False)
            if not est_iso:
                # Poids brute toujours recalcule cote serveur (le champ est en
                # lecture seule cote client) : poids brute = poids net + poids equipements.
                conteneur.poids_brute = (conteneur.poids_net or 0) + (conteneur.poids_equipements or 0)
            conteneur.save()
            conteneur.verifier_statut()

            messages.success(request, f"Empotage du conteneur {conteneur.reference} enregistré.")
            return redirect('DashboardAgentEmpotage:dossier-detail', dossier_id=conteneur.dossier_id)
    else:
        form = FormClass(instance=conteneur)

    return render(request, CREATE_TEMPLATE, {
        'dossier': conteneur.dossier,
        'conteneur': conteneur,
        'form': form,
        'est_iso': est_iso,
    })
