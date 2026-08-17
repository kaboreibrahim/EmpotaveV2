from django import template
from django.utils import dateformat, timezone

from apps.messaging.models import Conversation

register = template.Library()


@register.filter
def autre_utilisateur(conversation, viewer):
    """Pour une conversation privee : l'autre membre (pas `viewer`). None si
    non applicable (pas une conversation privee, ou pas encore chargee).
    Suppose `membres_conversation__user` prefetch — pas de requete de plus."""
    if conversation.type_conversation != Conversation.TYPE_PRIVEE or viewer is None:
        return None
    for membre in conversation.membres_conversation.all():
        if membre.user_id != viewer.id:
            return membre.user
    return None


@register.filter
def titre_affichage(conversation, viewer=None):
    """Titre lisible d'une conversation, quel que soit son type — evite de
    dupliquer ce if/elif dans chaque template (liste, detail, panneau).
    `viewer` (l'utilisateur connecte) sert a afficher le nom de l'autre
    personne pour une conversation privee."""
    if conversation.type_conversation == Conversation.TYPE_DOSSIER and conversation.dossier_id:
        return f"{conversation.dossier.TRD} — {conversation.dossier.projet}"
    if conversation.type_conversation == Conversation.TYPE_GROUPE:
        groupe = getattr(conversation, 'groupe', None)
        if groupe:
            return groupe.nom
    if conversation.type_conversation == Conversation.TYPE_PRIVEE:
        autre = autre_utilisateur(conversation, viewer)
        if autre is not None:
            return nom_affichage(autre)
    return conversation.titre or conversation.get_type_conversation_display()


@register.filter
def nom_affichage(user):
    """Nom lisible d'un utilisateur, y compris quand `user` est None
    (Message.auteur est SET_NULL : un compte supprime ne doit jamais faire
    planter l'affichage des messages qu'il a laisses).

    A utiliser plutot que `user.get_full_name|default:user.username` : ce
    chainage plante avec VariableDoesNotExist des que `user` est None, car un
    argument de filtre (apres le premier `|default:`) n'a pas le meme
    traitement silencieux qu'une variable de premier niveau dans Django."""
    if user is None:
        return "Utilisateur supprimé"
    return user.get_full_name() or user.username


@register.filter
def horodatage_court(dt):
    """Heure si aujourd'hui, 'Hier', jour abrege si cette semaine, sinon
    date courte — format compact type messagerie mobile pour la liste des
    conversations. Utilise dateformat.format (moteur du filtre `date`
    integre) plutot que strftime : reste en francais quelle que soit la
    locale du systeme d'exploitation du serveur."""
    if dt is None:
        return ''
    maintenant = timezone.localtime()
    dt_local = timezone.localtime(dt)
    if dt_local.date() == maintenant.date():
        return dateformat.format(dt_local, 'H:i')
    delta_jours = (maintenant.date() - dt_local.date()).days
    if delta_jours == 1:
        return 'Hier'
    if 0 < delta_jours < 7:
        return dateformat.format(dt_local, 'D')
    return dateformat.format(dt_local, 'd/m')


@register.filter
def duree_mmss(secondes):
    """Duree d'un vocal au format m:ss (ex. 1:05) — vide si inconnue."""
    if not secondes:
        return ''
    secondes = int(secondes)
    return f"{secondes // 60}:{secondes % 60:02d}"
