"""
apps/messaging/signals.py
A chaque creation/modification d'un Dossier (apps.conteneurs), on
(re)synchronise sa conversation principale (type DOSSIER) et ses membres
autorises, deduits des roles metier deja rattaches au dossier (client,
agent de selection, agent d'empotage, personnel, agent operationnel).

Un utilisateur reassigne plus tard sur un dossier est ajoute a la
conversation, mais un utilisateur retire d'un role n'en est jamais
automatiquement exclu : il garde acces a l'historique auquel il a participe.
Le retrait explicite, s'il est necessaire, reste une action manuelle.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.conteneurs.models import Dossier

from .models import Conversation, ConversationMember


def utilisateurs_autorises(dossier):
    """Utilisateurs deja rattaches au dossier via ses roles metier existants :
    ce sont eux, et seulement eux, qui doivent avoir acces a sa conversation."""
    users = set()
    if dossier.id_client_id and dossier.id_client.user_id:
        users.add(dossier.id_client.user)
    if dossier.Id_Agent_selection_id and dossier.Id_Agent_selection.user_id:
        users.add(dossier.Id_Agent_selection.user)
    if dossier.Id_Agent_empotage_id and dossier.Id_Agent_empotage.user_id:
        users.add(dossier.Id_Agent_empotage.user)
    if dossier.Id_Personnel_id and dossier.Id_Personnel.user_id:
        users.add(dossier.Id_Personnel.user)
    if dossier.Id_Agent_operationel_id and dossier.Id_Agent_operationel.user_id:
        users.add(dossier.Id_Agent_operationel.user)
    return users


@receiver(post_save, sender=Dossier)
def synchroniser_conversation_dossier(sender, instance, created, **kwargs):
    conversation, _ = Conversation.objects.get_or_create(
        dossier=instance,
        type_conversation=Conversation.TYPE_DOSSIER,
        defaults={'titre': f"Dossier {instance.TRD}"},
    )
    deja_membres = set(
        conversation.membres_conversation.values_list('user_id', flat=True)
    )
    for user in utilisateurs_autorises(instance):
        if user.pk not in deja_membres:
            ConversationMember.objects.create(conversation=conversation, user=user)
