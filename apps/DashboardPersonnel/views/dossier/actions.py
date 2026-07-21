from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect

from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.conteneurs.models import Dossier
from apps.notification.models import Notification
from apps.notification.services import notifier


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

    if dossier.Id_Agent_empotage:
        notifier(
            dossier.Id_Agent_empotage.user,
            f"Le dossier {dossier.TRD} — {dossier.projet} a été rétrogradé par "
            f"{request.user.get_full_name() or request.user.username} et nécessite une correction : "
            f"« {commentaire} »",
            categorie=Notification.CATEGORIE_ALERTE,
        )

    messages.success(request, f"Le dossier {dossier.projet} a été rétrogradé et l'agent d'empotage a été notifié.")
    return redirect('DashboardPersonnel:dossier-detail', pk=dossier.id)
