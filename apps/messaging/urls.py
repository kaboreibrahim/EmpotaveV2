from django.urls import path

from .views import (
    AttachmentDownloadView, ConversationDetailView, ConversationListView,
    DemarrerConversationPriveeView, GroupAddMembersView, GroupLeaveView, GroupRemoveMemberView,
    MessageAttachmentSendView, MessageDeleteView, MessageEditView, MessagesFragmentView, MessageSendView,
    NouveauGroupeView, NouvelleConversationView,
)

app_name = 'messaging'

urlpatterns = [
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/nouvelle/', NouvelleConversationView.as_view(), name='nouvelle-conversation'),
    path('conversations/nouveau-groupe/', NouveauGroupeView.as_view(), name='nouveau-groupe'),
    path(
        'conversations/demarrer/<int:user_id>/',
        DemarrerConversationPriveeView.as_view(),
        name='demarrer-conversation-privee',
    ),
    path('conversations/<uuid:conversation_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path(
        'conversations/<uuid:conversation_id>/membres/ajouter/',
        GroupAddMembersView.as_view(),
        name='groupe-ajouter-membres',
    ),
    path(
        'conversations/<uuid:conversation_id>/membres/<int:user_id>/retirer/',
        GroupRemoveMemberView.as_view(),
        name='groupe-retirer-membre',
    ),
    path(
        'conversations/<uuid:conversation_id>/quitter/',
        GroupLeaveView.as_view(),
        name='groupe-quitter',
    ),
    path(
        'conversations/<uuid:conversation_id>/messages/fragment/',
        MessagesFragmentView.as_view(),
        name='messages-fragment',
    ),
    path(
        'conversations/<uuid:conversation_id>/messages/envoyer/',
        MessageSendView.as_view(),
        name='message-envoyer',
    ),
    path(
        'conversations/<uuid:conversation_id>/messages/envoyer-fichier/',
        MessageAttachmentSendView.as_view(),
        name='message-envoyer-fichier',
    ),
    path('messages/<uuid:message_id>/modifier/', MessageEditView.as_view(), name='message-modifier'),
    path('messages/<uuid:message_id>/supprimer/', MessageDeleteView.as_view(), name='message-supprimer'),
    path(
        'pieces-jointes/<uuid:attachment_id>/telecharger/',
        AttachmentDownloadView.as_view(),
        name='attachment-download',
    ),
]
