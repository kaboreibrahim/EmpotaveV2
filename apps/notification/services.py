"""
apps/notification/services.py
Point d'entrée unique pour créer des notifications depuis les autres apps.

`NotificationService` centralise toute la logique métier de notification
(in-app + Web Push) : les vues ne doivent appeler que ses méthodes, jamais
manipuler directement `Notification`/`PushSubscription`.
"""
import logging

from django.urls import NoReverseMatch, reverse

from apps.users.models import Users

from .models import Notification
from .utils import send_web_push

logger = logging.getLogger(__name__)

# Nom de l'URL "détail dossier" (et de son kwarg) pour chaque tableau de bord,
# utilisé pour construire l'URL de redirection propre à chaque destinataire.
_DASHBOARD_URL_BY_ROLE = {
    'agent_selection': ('DashboardAgentSelection:dossier-detail', 'dossier_id'),
    'agent_empotage':  ('DashboardAgentEmpotage:dossier-detail', 'dossier_id'),
    'personnel':       ('DashboardPersonnel:dossier-detail', 'pk'),
    'client':          ('DashboardClient:dossier-detail', 'pk'),
    'comptable':       ('comptabiliteDashboard:dossier-detail', 'pk'),
}


def _dossier_url(dossier, role):
    entree = _DASHBOARD_URL_BY_ROLE.get(role)
    if not entree or dossier is None:
        return ''
    url_name, kwarg = entree
    try:
        return reverse(url_name, kwargs={kwarg: dossier.id})
    except NoReverseMatch:
        return ''


class NotificationService:
    """Toutes les notifications (in-app + Web Push) passent par cette classe."""

    # ------------------------------------------------------------------
    # Coeur du service : création + envoi, réutilisé par toutes les méthodes
    # métier ci-dessous ainsi que par `notifier()`/`notifier_personnel()`.
    # ------------------------------------------------------------------
    @staticmethod
    def creer_notification(users, message, titre='', type_notification=Notification.TYPE_AUTRE,
                            dossier=None, url='', categorie=Notification.CATEGORIE_INFO):
        """Crée une notification `message` pour chaque utilisateur de `users` et
        tente immédiatement l'envoi Web Push correspondant.

        Accepte un seul utilisateur ou un itérable ; les valeurs vides (None)
        sont ignorées pour ne pas planter quand un champ FK optionnel (ex:
        Id_Personnel) n'est pas renseigné sur le dossier. Un utilisateur sans
        abonnement Push, ou dont l'envoi échoue, n'interrompt jamais l'appelant.
        """
        if hasattr(users, 'pk'):
            users = [users]

        destinataires = []
        vus = set()
        for user in users:
            if not user or user.pk in vus:
                continue
            vus.add(user.pk)
            destinataires.append(user)

        if not destinataires:
            return []

        notifications = Notification.objects.bulk_create([
            Notification(
                user=user, message=message, titre=titre,
                type_notification=type_notification, dossier=dossier,
                url=url, categorie=categorie,
            )
            for user in destinataires
        ])

        for notification in notifications:
            NotificationService._envoyer_push(notification)

        return notifications

    @staticmethod
    def _envoyer_push(notification):
        """Envoie la notification Web Push à tous les abonnements de l'utilisateur.

        Un utilisateur sans abonnement (navigateur jamais autorisé) est un cas
        normal : on journalise et on continue sans interrompre l'appelant.
        """
        abonnements = notification.user.push_subscriptions.all()
        if not abonnements:
            return

        payload = {
            'title': notification.titre or 'Nouvelle notification',
            'body': notification.message,
            'url': notification.url or '/',
            'tag': notification.type_notification,
        }
        for abonnement in abonnements:
            try:
                send_web_push(abonnement, payload)
            except Exception:
                logger.exception(
                    "Échec inattendu de l'envoi Push pour l'utilisateur %s", notification.user_id,
                )

    # ------------------------------------------------------------------
    # Événements métier
    # ------------------------------------------------------------------
    @staticmethod
    def notify_dossier_created(dossier):
        """Un dossier vient d'être créé : les agents de sélection et les agents
        opérationnels concernés sont notifiés qu'il est prêt pour la sélection."""
        if dossier.Id_Agent_selection:
            destinataires_selection = [dossier.Id_Agent_selection.user]
        else:
            destinataires_selection = list(Users.objects.filter(user_type='agent_selection', is_active=True))

        if dossier.Id_Agent_operationel:
            destinataires_operationnel = [dossier.Id_Agent_operationel.user]
        else:
            destinataires_operationnel = list(Users.objects.filter(user_type='personnel', is_active=True))

        message = f"Le dossier {dossier.TRD} — {dossier.projet} est prêt pour la sélection."
        titre = "Nouveau dossier créé"

        NotificationService.creer_notification(
            destinataires_selection, message, titre,
            Notification.TYPE_DOSSIER_CREE, dossier, _dossier_url(dossier, 'agent_selection'),
        )
        NotificationService.creer_notification(
            destinataires_operationnel, message, titre,
            Notification.TYPE_DOSSIER_CREE, dossier, _dossier_url(dossier, 'personnel'),
        )

    @staticmethod
    def notify_payment_validated(dossier):
        """Le paiement d'un dossier vient d'être validé par le service comptable :
        agent de sélection, agent d'empotage, agent opérationnel et personnel
        peuvent démarrer/poursuivre son traitement."""
        message = (
            f"Le paiement du dossier {dossier.TRD} — {dossier.projet} a été validé : "
            "vous pouvez désormais commencer son traitement."
        )
        titre = "Paiement validé"

        if dossier.Id_Agent_selection:
            NotificationService.creer_notification(
                [dossier.Id_Agent_selection.user], message, titre,
                Notification.TYPE_PAIEMENT_VALIDE, dossier, _dossier_url(dossier, 'agent_selection'),
            )
        if dossier.Id_Agent_empotage:
            NotificationService.creer_notification(
                [dossier.Id_Agent_empotage.user], message, titre,
                Notification.TYPE_PAIEMENT_VALIDE, dossier, _dossier_url(dossier, 'agent_empotage'),
            )
        if dossier.Id_Agent_operationel:
            NotificationService.creer_notification(
                [dossier.Id_Agent_operationel.user], message, titre,
                Notification.TYPE_PAIEMENT_VALIDE, dossier, _dossier_url(dossier, 'personnel'),
            )
        NotificationService.creer_notification(
            Users.objects.filter(user_type='personnel', is_active=True), message, titre,
            Notification.TYPE_PAIEMENT_VALIDE, dossier, _dossier_url(dossier, 'personnel'),
        )

    # Messages de transition de statut : (ancien_statut, nouveau_statut) -> callable(dossier) -> liste de
    # (destinataires, message, role_pour_url).
    @staticmethod
    def _transitions_statut(dossier, ancien_statut, nouveau_statut):
        transitions = []

        if nouveau_statut == 'empotage_en_cours':
            if dossier.Id_Agent_empotage:
                transitions.append((
                    [dossier.Id_Agent_empotage.user],
                    f"Le dossier {dossier.TRD} — {dossier.projet} est prêt pour l'habillage & l'empotage.",
                    'agent_empotage',
                ))
            transitions.append((
                Users.objects.filter(user_type='personnel', is_active=True),
                f"Le dossier {dossier.TRD} — {dossier.projet} est passé en empotage.",
                'personnel',
            ))
            if dossier.id_client:
                transitions.append((
                    [dossier.id_client.user],
                    f"La sélection de votre dossier {dossier.TRD} — {dossier.projet} est terminée : "
                    "l'habillage & l'empotage démarrent.",
                    'client',
                ))

        elif nouveau_statut == 'dossier_termine':
            if dossier.Id_Agent_selection:
                transitions.append((
                    [dossier.Id_Agent_selection.user],
                    f"Le dossier {dossier.TRD} — {dossier.projet} a été empoté et clôturé.",
                    'agent_selection',
                ))
            transitions.append((
                Users.objects.filter(user_type='personnel', is_active=True),
                f"Le dossier {dossier.TRD} — {dossier.projet} est terminé.",
                'personnel',
            ))
            if dossier.id_client:
                transitions.append((
                    [dossier.id_client.user],
                    f"Votre dossier {dossier.TRD} — {dossier.projet} est terminé : le rapport est disponible.",
                    'client',
                ))

        elif nouveau_statut == 'selection_en_cours':
            if dossier.Id_Agent_selection:
                transitions.append((
                    [dossier.Id_Agent_selection.user],
                    f"Le dossier {dossier.TRD} — {dossier.projet} est prêt pour la sélection.",
                    'agent_selection',
                ))

        return transitions

    @staticmethod
    def notify_status_changed(dossier, ancien_statut=None, nouveau_statut=None):
        """Le statut d'un dossier vient de changer : chaque intervenant concerné
        par la nouvelle étape est notifié."""
        nouveau_statut = nouveau_statut or dossier.statut
        for destinataires, message, role in NotificationService._transitions_statut(
            dossier, ancien_statut, nouveau_statut
        ):
            NotificationService.creer_notification(
                destinataires, message, "Changement de statut",
                Notification.TYPE_CHANGEMENT_STATUT, dossier, _dossier_url(dossier, role),
            )

    @staticmethod
    def notify_document_added(document):
        """Un document vient d'être ajouté à un dossier : seuls l'agent
        opérationnel assigné et le client sont notifiés (hors la personne qui
        vient de le déposer)."""
        dossier = document.dossier
        message = (
            f"Un nouveau document ({document.type_document}) a été ajouté au dossier "
            f"{dossier.TRD} — {dossier.projet}."
        )
        deposant = getattr(document, 'ajoute_par', None)
        deposant_pk = getattr(deposant, 'pk', None)

        candidats = []
        if dossier.Id_Agent_operationel and dossier.Id_Agent_operationel.user_id != deposant_pk:
            candidats.append((dossier.Id_Agent_operationel.user, 'personnel'))
        if dossier.id_client and dossier.id_client.user_id != deposant_pk:
            candidats.append((dossier.id_client.user, 'client'))

        for user, role in candidats:
            NotificationService.creer_notification(
                [user], message, "Nouveau document ajouté",
                Notification.TYPE_DOCUMENT_AJOUTE, dossier, _dossier_url(dossier, role),
            )

    @staticmethod
    def notify_return_selection(dossier, commentaire, auteur):
        """Un dossier en empotage est retourné en sélection : seul l'agent de
        sélection assigné est notifié, avec le commentaire de correction."""
        if not dossier.Id_Agent_selection:
            return
        auteur_nom = auteur.get_full_name() or auteur.username
        NotificationService.creer_notification(
            [dossier.Id_Agent_selection.user],
            f"Le dossier {dossier.TRD} — {dossier.projet} a été retourné en sélection par "
            f"{auteur_nom} et nécessite une correction : « {commentaire} »",
            "Dossier retourné en sélection",
            Notification.TYPE_RETOUR_SELECTION,
            dossier,
            _dossier_url(dossier, 'agent_selection'),
            categorie=Notification.CATEGORIE_ALERTE,
        )

    @staticmethod
    def notify_return_empotage(dossier, commentaire, auteur):
        """Un dossier terminé est rétrogradé en empotage : seul l'agent
        d'empotage assigné est notifié, avec le commentaire de correction."""
        if not dossier.Id_Agent_empotage:
            return
        auteur_nom = auteur.get_full_name() or auteur.username
        NotificationService.creer_notification(
            [dossier.Id_Agent_empotage.user],
            f"Le dossier {dossier.TRD} — {dossier.projet} a été rétrogradé par "
            f"{auteur_nom} et nécessite une correction : « {commentaire} »",
            "Dossier rétrogradé en empotage",
            Notification.TYPE_RETOUR_EMPOTAGE,
            dossier,
            _dossier_url(dossier, 'agent_empotage'),
            categorie=Notification.CATEGORIE_ALERTE,
        )

    @staticmethod
    def notify_sync_conflict(dossier, auteur, role, message):
        """Une action mise en file d'attente hors ligne (voir apps/offline_sync)
        n'a pas pu être rejouée automatiquement car l'état du dossier/conteneur
        a changé entretemps : prévient l'auteur de l'action pour qu'il aille
        consulter l'état actuel et décide de l'abandonner ou de la rejouer."""
        NotificationService.creer_notification(
            [auteur],
            message,
            "Action hors ligne non appliquée",
            Notification.TYPE_AUTRE,
            dossier,
            _dossier_url(dossier, role),
            categorie=Notification.CATEGORIE_ALERTE,
        )


# ----------------------------------------------------------------------
# Compatibilité ascendante : fonctions historiques utilisées par les vues
# existantes (message libre, sans événement métier précis). Elles délèguent
# désormais à NotificationService, qui reste le seul point d'entrée réel.
# ----------------------------------------------------------------------
def notifier(users, message, categorie=Notification.CATEGORIE_INFO):
    return NotificationService.creer_notification(users, message, categorie=categorie)


def notifier_personnel(message):
    """Notifie tous les utilisateurs de type 'personnel' (pas seulement celui
    éventuellement assigné à un dossier via Id_Personnel)."""
    return notifier(Users.objects.filter(user_type='personnel', is_active=True), message)
