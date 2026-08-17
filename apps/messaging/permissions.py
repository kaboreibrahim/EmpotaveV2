"""
apps/messaging/permissions.py
Point de passage unique pour toute verification d'acces a une conversation
ou a une piece jointe. Aucune vue ne doit interroger Conversation ou
MessageAttachment directement par pk : c'est ce qui empeche un utilisateur
d'acceder a /messaging/conversations/16/ en modifiant l'URL depuis
/messaging/conversations/15/ (voir cahier des charges, section SECURITE).

On renvoie systematiquement Http404 (jamais 403) pour un acces refuse :
un 403 confirmerait l'existence de l'objet a quelqu'un qui n'y a pas droit.
"""
from django.http import Http404

from .models import Conversation, ConversationMember, Message, MessageAttachment


def conversations_visibles(user):
    """Les seules conversations que `user` a le droit de voir."""
    if not user.is_authenticated:
        return Conversation.objects.none()
    return Conversation.objects.filter(membres_conversation__user=user).distinct()


def est_membre(conversation, user) -> bool:
    if not user.is_authenticated:
        return False
    return ConversationMember.objects.filter(conversation=conversation, user=user).exists()


def est_admin_conversation(conversation, user) -> bool:
    """Un membre avec le role admin peut ajouter/retirer des membres d'un
    groupe. N'a de sens que pour une conversation de type groupe, mais reste
    correct (renvoie False) pour les autres types."""
    if not user.is_authenticated:
        return False
    return ConversationMember.objects.filter(
        conversation=conversation, user=user, role=ConversationMember.ROLE_ADMIN,
    ).exists()



def get_conversation_ou_404(user, conversation_id) -> Conversation:
    conversation = conversations_visibles(user).filter(pk=conversation_id).first()
    if conversation is None:
        raise Http404("Conversation introuvable.")
    return conversation


def get_message_ou_404(user, message_id) -> Message:
    message = (
        Message.objects
        .filter(pk=message_id, conversation__in=conversations_visibles(user))
        .select_related('conversation', 'auteur')
        .first()
    )
    if message is None:
        raise Http404("Message introuvable.")
    return message


def get_attachment_ou_404(user, attachment_id) -> MessageAttachment:
    attachment = (
        MessageAttachment.objects
        .filter(pk=attachment_id, message__conversation__in=conversations_visibles(user))
        .select_related('message', 'message__conversation')
        .first()
    )
    if attachment is None:
        raise Http404("Pièce jointe introuvable.")
    return attachment
