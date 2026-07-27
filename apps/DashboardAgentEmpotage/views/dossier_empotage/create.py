from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.conteneurs.models import Flexitanks, ISOTanks
from apps.conteneurs.services import verifier_paiement
from apps.DashboardAgentEmpotage.forms import FlexitankEmpotageForm, ISOTankEmpotageForm
from apps.notification.services import NotificationService
from apps.offline_sync.utils import (
    action_deja_appliquee,
    date_modifier_correspond,
    enregistrer_action_synchronisee,
    reponse_conflit,
)

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


def _etat_conteneur_json(conteneur):
    return {
        'id': str(conteneur.pk),
        'statut': conteneur.statut,
        'statut_display': conteneur.get_statut_display(),
        'poids_net': str(conteneur.poids_net) if conteneur.poids_net is not None else None,
        'date_modifier': int(conteneur.date_modifier.timestamp()),
    }


@login_required
@require_POST
def renseigner_empotage_ajax(request, pk):
    """Variante JSON de `renseigner_empotage`, rejouable par le Service Worker
    (voir apps/offline_sync et static/notification/js/service-worker.js) une
    fois la connexion revenue. Reutilise la meme portee agent (ownership via
    Id_Agent_empotage, pas de permission Django separee : identique a la vue
    page-complete), mais ne leve jamais un Http404 generique quand l'etat a
    bouge entretemps — retourne un 409 explicite avec l'etat courant, pour
    que le rejeu hors ligne ne se solde jamais par un echec silencieux."""
    client_action_id = request.POST.get('client_action_id')
    resultat_existant = action_deja_appliquee(client_action_id, request.user)
    if resultat_existant is not None:
        return JsonResponse(resultat_existant.result_snapshot)

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
        return JsonResponse({'success': False, 'error': "Conteneur introuvable ou non attribué à cet agent."}, status=404)

    def _signaler_conflit():
        NotificationService.notify_sync_conflict(
            conteneur.dossier, request.user, 'agent_empotage',
            f"Votre saisie d'empotage hors ligne pour le conteneur {conteneur.reference} n'a pas pu "
            "être appliquée : le dossier a changé d'état entretemps. Merci de vérifier et de ressaisir si besoin.",
        )
        return reponse_conflit(_etat_conteneur_json(conteneur))

    if not date_modifier_correspond(conteneur, request.POST.get('client_date_modifier')):
        return _signaler_conflit()

    verifier_paiement(conteneur.dossier)
    if conteneur.dossier.statut not in STATUTS_OUVERTS_A_L_EMPOTAGE:
        return _signaler_conflit()

    FormClass = ISOTankEmpotageForm if est_iso else FlexitankEmpotageForm
    form = FormClass(request.POST, request.FILES, instance=conteneur)
    if not form.is_valid():
        return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    conteneur = form.save(commit=False)
    if not est_iso:
        conteneur.poids_brute = (conteneur.poids_net or 0) + (conteneur.poids_equipements or 0)
    conteneur.save()
    conteneur.verifier_statut()
    conteneur.refresh_from_db()

    snapshot = {'success': True, 'conteneur': _etat_conteneur_json(conteneur)}
    if client_action_id:
        enregistrer_action_synchronisee(client_action_id, request.user, 'renseigner_empotage', snapshot)
    return JsonResponse(snapshot)
