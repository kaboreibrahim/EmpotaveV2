"""
apps/messaging/services.py
Logique metier des messages : envoi, edition, suppression (soft), pagination
et suivi de lecture. Les vues ne doivent manipuler Message/MessageRead qu'a
travers ce module — ca garde la notification et la mise a jour de
Conversation.date_modifier a un seul endroit, jamais oubliables dans une vue.
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.notification.models import Notification
from apps.notification.services import NotificationService

from .attachments import creer_piece_jointe
from .models import Conversation, ConversationMember, Group, Message, MessageRead

MESSAGES_PAR_PAGE = 30


def envoyer_message(conversation, auteur, contenu, reponse_a=None):
    """Cree un message texte, met a jour la date d'activite de la conversation
    (utilisee pour le tri de la liste), notifie les autres membres et diffuse
    l'evenement aux clients connectes (voir apps.messaging.consumers)."""
    message = Message.objects.create(
        conversation=conversation, auteur=auteur, type_message=Message.TYPE_TEXTE,
        contenu=contenu, reponse_a=reponse_a,
    )
    conversation.save(update_fields=['date_modifier'])
    _notifier_nouveau_message(message)
    _diffuser(conversation, 'nouveau.message')
    return message


def envoyer_message_avec_fichier(conversation, auteur, uploaded_file, contenu='', duree_secondes=None):
    """Comme `envoyer_message`, mais pour une piece jointe (image/video/
    document/vocal — voir apps.messaging.attachments). Peut lever
    FichierInvalide : dans ce cas rien n'est ecrit (transaction annulee)."""
    with transaction.atomic():
        message = Message.objects.create(
            conversation=conversation, auteur=auteur, type_message=Message.TYPE_DOCUMENT,
            contenu=contenu,
        )
        piece_jointe = creer_piece_jointe(message, uploaded_file, duree_secondes=duree_secondes)
        if piece_jointe.type_fichier != message.type_message:
            message.type_message = piece_jointe.type_fichier
            message.save(update_fields=['type_message'])

    conversation.save(update_fields=['date_modifier'])
    _notifier_nouveau_message(message)
    _diffuser(conversation, 'nouveau.message')
    return message


def get_or_create_conversation_privee(user_a, user_b):
    """Renvoie la conversation privee entre ces deux utilisateurs, en la
    creant si elle n'existe pas encore. Une seule conversation privee par
    paire (peu importe l'ordre A/B) — jamais de doublon a chaque nouveau
    message."""
    if user_a.id == user_b.id:
        raise ValueError("Un utilisateur ne peut pas demarrer une conversation privee avec lui-meme.")

    # Deux .filter() distincts (pas un seul avec user__in=[a, b]) : chacun
    # doit matcher une ligne ConversationMember differente, pour exiger que
    # LES DEUX utilisateurs soient membres de la meme conversation — pas
    # juste l'un ou l'autre.
    existante = (
        Conversation.objects
        .filter(type_conversation=Conversation.TYPE_PRIVEE, membres_conversation__user=user_a)
        .filter(membres_conversation__user=user_b)
        .first()
    )
    if existante:
        return existante

    with transaction.atomic():
        conversation = Conversation.objects.create(type_conversation=Conversation.TYPE_PRIVEE)
        ConversationMember.objects.create(conversation=conversation, user=user_a)
        ConversationMember.objects.create(conversation=conversation, user=user_b)
    return conversation


def creer_groupe(createur, nom, description='', photo=None, dossier=None, membres=()):
    """Cree un groupe : sa conversation, sa fiche Group, et les
    ConversationMember correspondants — le createur est admin d'office (voir
    cahier des charges : `Group` n'a pas de modele GroupMember separe, la
    liste des membres vit sur `ConversationMember`)."""
    with transaction.atomic():
        conversation = Conversation.objects.create(type_conversation=Conversation.TYPE_GROUPE, dossier=dossier)
        groupe = Group.objects.create(
            conversation=conversation, nom=nom, description=description, photo=photo, cree_par=createur,
        )
        ConversationMember.objects.create(
            conversation=conversation, user=createur, role=ConversationMember.ROLE_ADMIN,
        )
        autres = [m for m in membres if m.id != createur.id]
        for membre in autres:
            ConversationMember.objects.get_or_create(conversation=conversation, user=membre)

    _notifier_ajout_groupe(groupe, autres)
    return groupe


def ajouter_membres_groupe(groupe, utilisateurs):
    """Ajoute des utilisateurs a un groupe (deja membres ignores). Notifie
    uniquement ceux effectivement ajoutes."""
    conversation = groupe.conversation
    nouveaux = []
    for utilisateur in utilisateurs:
        _membre, cree = ConversationMember.objects.get_or_create(conversation=conversation, user=utilisateur)
        if cree:
            nouveaux.append(utilisateur)
    if nouveaux:
        _notifier_ajout_groupe(groupe, nouveaux)
        conversation.save(update_fields=['date_modifier'])
    return nouveaux


def retirer_membre_groupe(groupe, membre_a_retirer):
    """Retire un membre du groupe (retrait par un admin, ou depart
    volontaire). Si c'etait le dernier admin, promeut automatiquement le
    membre restant le plus ancien — un groupe ne doit jamais se retrouver
    sans aucun admin pour gerer ses membres."""
    conversation = groupe.conversation
    etait_admin = ConversationMember.objects.filter(
        conversation=conversation, user=membre_a_retirer, role=ConversationMember.ROLE_ADMIN,
    ).exists()
    ConversationMember.objects.filter(conversation=conversation, user=membre_a_retirer).delete()

    if etait_admin:
        reste_un_admin = ConversationMember.objects.filter(
            conversation=conversation, role=ConversationMember.ROLE_ADMIN,
        ).exists()
        if not reste_un_admin:
            plus_ancien = (
                ConversationMember.objects.filter(conversation=conversation).order_by('date_ajout').first()
            )
            if plus_ancien:
                plus_ancien.role = ConversationMember.ROLE_ADMIN
                plus_ancien.save(update_fields=['role'])


def _notifier_ajout_groupe(groupe, utilisateurs):
    if not utilisateurs:
        return
    NotificationService.creer_notification(
        utilisateurs, f"Vous avez été ajouté au groupe {groupe.nom}.", "Ajout à un groupe",
        Notification.TYPE_AJOUT_GROUPE, dossier=groupe.conversation.dossier,
        url=reverse('messaging:conversation-detail', args=[groupe.conversation.id]),
    )


def modifier_message(message, contenu):
    message.contenu = contenu
    message.save(update_fields=['contenu', 'date_modifier'])
    _diffuser(message.conversation, 'message.modifie')
    return message


def supprimer_message(message):
    """Suppression douce : le message reste en base (voir MessageRead,
    reponses...) mais s'affiche comme supprime cote UI."""
    message.est_supprime = True
    message.save(update_fields=['est_supprime', 'date_modifier'])
    _diffuser(message.conversation, 'message.supprime')
    return message


def _diffuser(conversation, type_evenement):
    """Signale aux clients connectes sur cette conversation qu'il faut
    recharger le fragment des messages. Pas de payload metier ici (le
    consumer ne renvoie que `{'type': ...}`) : le navigateur refait un fetch
    HTML classique, la logique de rendu reste uniquement cote Django."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f'conversation_{conversation.id}', {'type': type_evenement},
    )


def messages_pagines(conversation, limite=MESSAGES_PAR_PAGE):
    """Les `limite` messages les plus recents, en ordre chronologique. Ne
    charge jamais toute la conversation d'un coup (voir cahier des charges,
    section PERFORMANCE)."""
    total = conversation.messages.count()
    messages = list(
        conversation.messages
        .select_related('auteur', 'reponse_a', 'reponse_a__auteur')
        .prefetch_related('pieces_jointes')
        .order_by('-date_created')[:limite]
    )
    messages.reverse()
    return messages, total > len(messages)


def marquer_comme_lu(conversation, user, messages_affiches):
    """Avance le pointeur de lecture rapide (ConversationMember) au dernier
    message affiche, et enregistre une lecture par message (MessageRead) pour
    les messages qui ne sont pas deja marques lus par cet utilisateur."""
    if not messages_affiches:
        return
    dernier = messages_affiches[-1]
    ConversationMember.objects.filter(conversation=conversation, user=user).update(
        dernier_message_lu=dernier, date_dernier_lu=timezone.now(),
    )
    deja_lus = set(
        MessageRead.objects
        .filter(user=user, message__in=messages_affiches)
        .values_list('message_id', flat=True)
    )
    a_creer = [
        MessageRead(message=m, user=user)
        for m in messages_affiches
        if m.id not in deja_lus and m.auteur_id != user.id
    ]
    if a_creer:
        MessageRead.objects.bulk_create(a_creer, ignore_conflicts=True)


def _notifier_nouveau_message(message):
    conversation = message.conversation
    auteur = message.auteur
    destinataires = [
        membre.user for membre in conversation.membres_conversation.select_related('user').all()
        if membre.user_id != auteur.id and membre.notifications_actives
    ]
    if not destinataires:
        return

    auteur_nom = auteur.get_full_name() or auteur.username
    if conversation.type_conversation == Conversation.TYPE_DOSSIER and conversation.dossier_id:
        texte = f"Nouveau message dans {conversation.dossier.TRD}."
    else:
        texte = f"{auteur_nom} vous a envoyé un message."

    NotificationService.creer_notification(
        destinataires, texte, "Nouveau message", Notification.TYPE_NOUVEAU_MESSAGE,
        dossier=conversation.dossier, url=reverse('messaging:conversation-detail', args=[conversation.id]),
    )
