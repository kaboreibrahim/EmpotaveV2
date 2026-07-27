from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.conteneurs.models import Dossier
from apps.notification.services import NotificationService
from apps.offline_sync.utils import (
    action_deja_appliquee,
    date_modifier_correspond,
    enregistrer_action_synchronisee,
    reponse_conflit,
)


@login_required
@permission_required('conteneurs.change_dossier', raise_exception=True)
def retrograder_dossier(request, dossier_id):
    """Rouvre un dossier termine (retour en empotage_en_cours) avec un commentaire
    obligatoire, envoye a l'agent d'empotage pour lui expliquer la correction attendue."""
    dossier = get_object_or_404(Dossier, id=dossier_id)

    if dossier.statut != 'dossier_termine':
        messages.error(request, "Seul un dossier terminé peut être rétrogradé.")
        return redirect('DashboardPersonnel:dossier-detail', pk=dossier.id)

    commentaire = request.POST.get('commentaire', '').strip()
    if not commentaire:
        messages.error(request, "Un commentaire est obligatoire pour rétrograder un dossier.")
        return redirect('DashboardPersonnel:dossier-detail', pk=dossier.id)

    dossier.retrograder_apres_terminaison()
    log_action(dossier, AuditLog.ACTION_UPDATE, extra={
        'evenement': 'retrogradation',
        'commentaire': commentaire,
    })

    NotificationService.notify_return_empotage(dossier, commentaire, request.user)

    messages.success(request, f"Le dossier {dossier.projet} a été rétrogradé et l'agent d'empotage a été notifié.")
    return redirect('DashboardPersonnel:dossier-detail', pk=dossier.id)


@login_required
@permission_required('conteneurs.change_dossier', raise_exception=True)
def retour_selection_dossier(request, dossier_id):
    """Renvoie un dossier en empotage vers la sélection (retour en selection_en_cours) avec
    un commentaire obligatoire, envoyé a l'agent de sélection pour lui expliquer la correction
    attendue."""
    dossier = get_object_or_404(Dossier, id=dossier_id)

    if dossier.statut != 'empotage_en_cours':
        messages.error(request, "Seul un dossier en empotage peut être retourné en sélection.")
        return redirect('DashboardPersonnel:dossier-detail', pk=dossier.id)

    commentaire = request.POST.get('commentaire', '').strip()
    if not commentaire:
        messages.error(request, "Un commentaire est obligatoire pour retourner un dossier en sélection.")
        return redirect('DashboardPersonnel:dossier-detail', pk=dossier.id)

    dossier.retourner_en_selection()
    log_action(dossier, AuditLog.ACTION_UPDATE, extra={
        'evenement': 'retour_selection',
        'commentaire': commentaire,
    })

    NotificationService.notify_return_selection(dossier, commentaire, request.user)

    messages.success(request, f"Le dossier {dossier.projet} a été retourné en sélection et l'agent de sélection a été notifié.")
    return redirect('DashboardPersonnel:dossier-detail', pk=dossier.id)


# =============================================================================
# Variantes JSON, rejouables par le Service Worker (voir apps/offline_sync et
# static/notification/js/service-worker.js) une fois la connexion revenue.
# Contrairement aux méthodes du modèle (Dossier.retrograder_apres_terminaison/
# retourner_en_selection), qui ne font rien silencieusement si l'état a bougé,
# ces vues renvoient toujours un 409 explicite dans ce cas — jamais un rejeu
# hors ligne qui échoue sans que personne ne s'en aperçoive.
# =============================================================================

def _etat_dossier_json(dossier):
    return {
        'id': str(dossier.pk),
        'statut': dossier.statut,
        'statut_display': dossier.get_statut_display(),
        'date_modifier': int(dossier.date_modifier.timestamp()),
    }


def _signaler_conflit_dossier(dossier, user, message):
    NotificationService.notify_sync_conflict(dossier, user, 'personnel', message)
    return reponse_conflit(_etat_dossier_json(dossier))


@login_required
@permission_required('conteneurs.change_dossier', raise_exception=True)
@require_POST
def retrograder_dossier_ajax(request, dossier_id):
    client_action_id = request.POST.get('client_action_id')
    resultat_existant = action_deja_appliquee(client_action_id, request.user)
    if resultat_existant is not None:
        return JsonResponse(resultat_existant.result_snapshot)

    dossier = get_object_or_404(Dossier, id=dossier_id)

    if not date_modifier_correspond(dossier, request.POST.get('client_date_modifier')):
        return _signaler_conflit_dossier(
            dossier, request.user,
            f"Votre rétrogradation hors ligne du dossier {dossier.TRD} — {dossier.projet} n'a pas pu être "
            "appliquée : le dossier a changé d'état entretemps.",
        )
    if dossier.statut != 'dossier_termine':
        return _signaler_conflit_dossier(
            dossier, request.user,
            f"Votre rétrogradation hors ligne du dossier {dossier.TRD} — {dossier.projet} n'a pas pu être "
            "appliquée : seul un dossier terminé peut être rétrogradé, et ce n'est plus le cas.",
        )

    commentaire = request.POST.get('commentaire', '').strip()
    if not commentaire:
        return JsonResponse({'success': False, 'errors': {'commentaire': ["Un commentaire est obligatoire."]}}, status=400)

    dossier.retrograder_apres_terminaison()
    log_action(dossier, AuditLog.ACTION_UPDATE, extra={'evenement': 'retrogradation', 'commentaire': commentaire})
    NotificationService.notify_return_empotage(dossier, commentaire, request.user)
    dossier.refresh_from_db()

    snapshot = {'success': True, 'dossier': _etat_dossier_json(dossier)}
    if client_action_id:
        enregistrer_action_synchronisee(client_action_id, request.user, 'retrograder_dossier', snapshot)
    return JsonResponse(snapshot)


@login_required
@permission_required('conteneurs.change_dossier', raise_exception=True)
@require_POST
def retour_selection_dossier_ajax(request, dossier_id):
    client_action_id = request.POST.get('client_action_id')
    resultat_existant = action_deja_appliquee(client_action_id, request.user)
    if resultat_existant is not None:
        return JsonResponse(resultat_existant.result_snapshot)

    dossier = get_object_or_404(Dossier, id=dossier_id)

    if not date_modifier_correspond(dossier, request.POST.get('client_date_modifier')):
        return _signaler_conflit_dossier(
            dossier, request.user,
            f"Votre retour en sélection hors ligne du dossier {dossier.TRD} — {dossier.projet} n'a pas pu être "
            "appliqué : le dossier a changé d'état entretemps.",
        )
    if dossier.statut != 'empotage_en_cours':
        return _signaler_conflit_dossier(
            dossier, request.user,
            f"Votre retour en sélection hors ligne du dossier {dossier.TRD} — {dossier.projet} n'a pas pu être "
            "appliqué : seul un dossier en empotage peut être retourné en sélection, et ce n'est plus le cas.",
        )

    commentaire = request.POST.get('commentaire', '').strip()
    if not commentaire:
        return JsonResponse({'success': False, 'errors': {'commentaire': ["Un commentaire est obligatoire."]}}, status=400)

    dossier.retourner_en_selection()
    log_action(dossier, AuditLog.ACTION_UPDATE, extra={'evenement': 'retour_selection', 'commentaire': commentaire})
    NotificationService.notify_return_selection(dossier, commentaire, request.user)
    dossier.refresh_from_db()

    snapshot = {'success': True, 'dossier': _etat_dossier_json(dossier)}
    if client_action_id:
        enregistrer_action_synchronisee(client_action_id, request.user, 'retour_selection_dossier', snapshot)
    return JsonResponse(snapshot)
