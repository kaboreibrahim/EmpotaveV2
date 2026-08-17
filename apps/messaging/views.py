"""
apps/messaging/views.py
Vues de messagerie : liste des conversations, detail d'une conversation
(messages + composeur), envoi/edition/suppression de message, fragment HTML
pour le rafraichissement temps reel (WebSocket ou repli polling — voir
static/messaging/js/realtime.js). Rendu HTML classique, comme le reste du
monolithe — pas d'API separee.
"""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import OuterRef, Q, Subquery
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.conteneurs.models import Dossier
from apps.users.models import Users

from .attachments import FichierInvalide
from .models import Conversation, Message, MessageAttachment
from .permissions import (
    conversations_visibles, est_admin_conversation, get_attachment_ou_404, get_conversation_ou_404,
    get_message_ou_404,
)
from .roles import base_template_name, dashboard_url_name, dossiers_url_name
from .routing import ws_path
from .services import (
    MESSAGES_PAR_PAGE, ajouter_membres_groupe, creer_groupe, envoyer_message, envoyer_message_avec_fichier,
    get_or_create_conversation_privee, marquer_comme_lu, messages_pagines, modifier_message,
    retirer_membre_groupe, supprimer_message,
)

ANNUAIRE_LIMITE = 50

FICHIERS_PARTAGES_LIMITE = 60


def _fichiers_partages(conversation):
    """Pieces jointes echangees dans la conversation, groupees par type pour
    la section "Fichiers" (cf. cahier des charges). Bornee : jamais toute
    l'historique d'un coup, cf. section PERFORMANCE."""
    attachments = (
        MessageAttachment.objects
        .filter(message__conversation=conversation, message__est_supprime=False)
        .select_related('message', 'message__auteur')
        .order_by('-date_created')[:FICHIERS_PARTAGES_LIMITE]
    )
    par_categorie = {'image': [], 'video': [], 'document': [], 'audio': []}
    for piece in attachments:
        par_categorie.setdefault(piece.type_fichier, []).append(piece)
    return par_categorie


def _navigation_context(user):
    dashboard_name = dashboard_url_name(user.user_type)
    dossiers_name = dossiers_url_name(user.user_type)
    return {
        'url_dashboard': reverse(dashboard_name) if dashboard_name else None,
        'url_dossiers': reverse(dossiers_name) if dossiers_name else None,
        'base_template': base_template_name(user.user_type),
    }


def _conversations_groupees(user, q=''):
    """Les conversations de l'utilisateur, groupees par type (Recentes /
    Groupes / Dossiers) pour le panneau de gauche, avec un aperçu du dernier
    message (sous-requete correlee : une seule requete SQL, jamais une
    requete par ligne — cf. section PERFORMANCE)."""
    dernier_message = (
        Message.objects
        .filter(conversation=OuterRef('pk'), est_supprime=False)
        .order_by('-date_created')
    )
    conversations = (
        conversations_visibles(user)
        .select_related('dossier', 'groupe')
        .prefetch_related('membres_conversation__user')
        .annotate(
            dernier_message_contenu=Subquery(dernier_message.values('contenu')[:1]),
            dernier_message_type=Subquery(dernier_message.values('type_message')[:1]),
        )
        .order_by('-date_modifier')
    )

    q = q.strip()
    if q:
        conversations = conversations.filter(
            Q(dossier__TRD__icontains=q) | Q(dossier__projet__icontains=q)
            | Q(titre__icontains=q) | Q(groupe__nom__icontains=q)
        ).distinct()

    conversations = list(conversations)
    privees = [c for c in conversations if c.type_conversation == Conversation.TYPE_PRIVEE]
    groupes = [c for c in conversations if c.type_conversation == Conversation.TYPE_GROUPE]
    dossiers = [c for c in conversations if c.type_conversation == Conversation.TYPE_DOSSIER]
    return {
        'conversations_privee': privees,
        'conversations_groupe': groupes,
        'conversations_dossier': dossiers,
        'groupes': [('Récentes', privees), ('Groupes', groupes), ('Dossiers', dossiers)],
    }


def _utilisateurs_annuaire(viewer, q=''):
    """Annuaire ouvert a tous les utilisateurs actifs (voir cahier des
    charges) pour demarrer une conversation privee — borne, une recherche
    plus precise est demandee au-dela plutot que de tout charger."""
    utilisateurs = (
        Users.objects
        .filter(is_active=True, deleted__isnull=True)
        .exclude(pk=viewer.pk)
        .select_related('entreprise')
        .order_by('first_name', 'last_name', 'username')
    )
    q = q.strip()
    if q:
        utilisateurs = utilisateurs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
            | Q(username__icontains=q) | Q(email__icontains=q)
        )
    return utilisateurs[:ANNUAIRE_LIMITE]


def _dossiers_disponibles(user):
    """Dossiers pour lesquels `user` a deja une conversation de type dossier
    visible — sert a limiter le choix de rattachement d'un groupe aux
    dossiers auxquels l'utilisateur a reellement acces, jamais tous les
    dossiers de la base."""
    dossier_ids = (
        conversations_visibles(user)
        .filter(type_conversation=Conversation.TYPE_DOSSIER)
        .values_list('dossier_id', flat=True)
    )
    return Dossier.objects.filter(id__in=dossier_ids).order_by('-date_created')


def _limite_demandee(request):
    try:
        limite = int(request.GET.get('limite', MESSAGES_PAR_PAGE))
    except (TypeError, ValueError):
        return MESSAGES_PAR_PAGE
    return max(MESSAGES_PAR_PAGE, min(limite, 300))


def _messages_context(request, conversation, limite):
    messages_conversation, a_plus_anciens = messages_pagines(conversation, limite)
    marquer_comme_lu(conversation, request.user, messages_conversation)
    return {
        'conversation': conversation,
        'messages_conversation': messages_conversation,
        'a_plus_anciens': a_plus_anciens,
        'limite_suivante': limite + MESSAGES_PAR_PAGE,
    }


class ConversationListView(LoginRequiredMixin, View):
    template_name = 'messaging/liste.html'

    def get(self, request, *args, **kwargs):
        q = request.GET.get('q', '')
        context = {
            'q': q,
            'conversation_active_id': None,
            **_conversations_groupees(request.user, q=q),
            **_navigation_context(request.user),
        }
        return render(request, self.template_name, context)


class ConversationDetailView(LoginRequiredMixin, View):
    template_name = 'messaging/detail.html'

    def get(self, request, conversation_id, *args, **kwargs):
        conversation = get_conversation_ou_404(request.user, conversation_id)
        membres = (
            conversation.membres_conversation
            .select_related('user')
            .order_by('user__first_name', 'user__username')
        )

        context = {
            'membres': membres,
            'est_admin_groupe': est_admin_conversation(conversation, request.user),
            'ws_url': ws_path(conversation.id, absolute=True, secure=request.is_secure(), host=request.get_host()),
            'fichiers_partages': _fichiers_partages(conversation),
            'q': '',
            'conversation_active_id': conversation.id,
            **_messages_context(request, conversation, _limite_demandee(request)),
            **_conversations_groupees(request.user),
            **_navigation_context(request.user),
        }
        return render(request, self.template_name, context)


class NouvelleConversationView(LoginRequiredMixin, View):
    """Annuaire pour demarrer une conversation privee (recherche + liste).

    Contexte separe en `q` (recherche du panneau de conversations, laissee
    vide ici) et `q_utilisateur` (recherche de CETTE page) : les deux
    templates partagent le meme contexte via l'include du panneau, un seul
    `q` commun aurait pre-rempli le panneau avec la recherche d'utilisateur."""
    template_name = 'messaging/nouvelle_conversation.html'

    def get(self, request, *args, **kwargs):
        q_utilisateur = request.GET.get('q', '')
        context = {
            'q': '',
            'q_utilisateur': q_utilisateur,
            'utilisateurs': _utilisateurs_annuaire(request.user, q=q_utilisateur),
            'conversation_active_id': None,
            **_conversations_groupees(request.user),
            **_navigation_context(request.user),
        }
        return render(request, self.template_name, context)


class DemarrerConversationPriveeView(LoginRequiredMixin, View):
    """Cree (ou reutilise) la conversation privee avec `user_id` et y
    redirige. Jamais de doublon — voir services.get_or_create_conversation_privee."""

    def post(self, request, user_id, *args, **kwargs):
        autre = get_object_or_404(Users, pk=user_id, is_active=True, deleted__isnull=True)
        if autre.id == request.user.id:
            raise PermissionDenied("Impossible de démarrer une conversation avec vous-même.")

        conversation = get_or_create_conversation_privee(request.user, autre)
        return redirect('messaging:conversation-detail', conversation_id=conversation.id)


class NouveauGroupeView(LoginRequiredMixin, View):
    """Creation d'un groupe : nom, description, photo, dossier de
    rattachement optionnel, membres choisis dans l'annuaire. Le createur
    devient admin d'office (voir services.creer_groupe)."""
    template_name = 'messaging/nouveau_groupe.html'

    def get(self, request, *args, **kwargs):
        context = {
            'q': '',
            'utilisateurs': _utilisateurs_annuaire(request.user),
            'dossiers_disponibles': _dossiers_disponibles(request.user),
            'conversation_active_id': None,
            **_conversations_groupees(request.user),
            **_navigation_context(request.user),
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        nom = request.POST.get('nom', '').strip()
        if not nom:
            messages.error(request, "Le nom du groupe est obligatoire.")
            return redirect('messaging:nouveau-groupe')

        description = request.POST.get('description', '').strip()
        photo = request.FILES.get('photo')

        dossier = None
        dossier_id = request.POST.get('dossier_id', '').strip()
        if dossier_id:
            dossier = _dossiers_disponibles(request.user).filter(pk=dossier_id).first()

        membre_ids = request.POST.getlist('membres')
        membres = Users.objects.filter(pk__in=membre_ids, is_active=True, deleted__isnull=True)

        groupe = creer_groupe(
            request.user, nom, description=description, photo=photo, dossier=dossier, membres=membres,
        )
        return redirect('messaging:conversation-detail', conversation_id=groupe.conversation_id)


class GroupAddMembersView(LoginRequiredMixin, View):
    """Ajout de membres a un groupe existant — reserve aux admins du groupe
    (voir permissions.est_admin_conversation). L'utilisateur est bien membre
    de la conversation (donc 403, pas 404, s'il n'est pas admin) : le 404
    reste reserve a ceux qui n'ont carrement pas acces a la conversation."""
    template_name = 'messaging/groupe_ajouter_membres.html'

    def _groupe_ou_refuse(self, request, conversation_id):
        conversation = get_conversation_ou_404(request.user, conversation_id)
        if conversation.type_conversation != Conversation.TYPE_GROUPE:
            raise Http404("Conversation introuvable.")
        if not est_admin_conversation(conversation, request.user):
            raise PermissionDenied("Seuls les administrateurs du groupe peuvent ajouter des membres.")
        return conversation.groupe

    def get(self, request, conversation_id, *args, **kwargs):
        groupe = self._groupe_ou_refuse(request, conversation_id)
        deja_membres = set(groupe.conversation.membres_conversation.values_list('user_id', flat=True))
        utilisateurs = [u for u in _utilisateurs_annuaire(request.user) if u.id not in deja_membres]
        context = {
            'groupe': groupe,
            'q': '',
            'utilisateurs': utilisateurs,
            'conversation_active_id': groupe.conversation_id,
            **_conversations_groupees(request.user),
            **_navigation_context(request.user),
        }
        return render(request, self.template_name, context)

    def post(self, request, conversation_id, *args, **kwargs):
        groupe = self._groupe_ou_refuse(request, conversation_id)
        membre_ids = request.POST.getlist('membres')
        utilisateurs = Users.objects.filter(pk__in=membre_ids, is_active=True, deleted__isnull=True)
        ajouter_membres_groupe(groupe, utilisateurs)
        return redirect('messaging:conversation-detail', conversation_id=groupe.conversation_id)


class GroupRemoveMemberView(LoginRequiredMixin, View):
    """Retrait d'un membre par un admin. Voir services.retirer_membre_groupe
    pour la promotion automatique si c'etait le dernier admin."""

    def post(self, request, conversation_id, user_id, *args, **kwargs):
        conversation = get_conversation_ou_404(request.user, conversation_id)
        if conversation.type_conversation != Conversation.TYPE_GROUPE:
            raise Http404("Conversation introuvable.")
        if not est_admin_conversation(conversation, request.user):
            raise PermissionDenied("Seuls les administrateurs du groupe peuvent retirer un membre.")

        membre = get_object_or_404(Users, pk=user_id)
        retirer_membre_groupe(conversation.groupe, membre)
        return redirect('messaging:conversation-detail', conversation_id=conversation.id)


class GroupLeaveView(LoginRequiredMixin, View):
    """Depart volontaire d'un groupe — accessible a tout membre, admin ou
    non (contrairement au retrait d'un tiers, reserve aux admins)."""

    def post(self, request, conversation_id, *args, **kwargs):
        conversation = get_conversation_ou_404(request.user, conversation_id)
        if conversation.type_conversation != Conversation.TYPE_GROUPE:
            raise Http404("Conversation introuvable.")

        retirer_membre_groupe(conversation.groupe, request.user)
        return redirect('messaging:conversation-list')


class MessagesFragmentView(LoginRequiredMixin, View):
    """Fragment HTML (juste la liste des messages) utilise par le JS temps
    reel pour rafraichir la conversation sans recharger la page entiere."""
    template_name = 'messaging/_messages_canvas.html'

    def get(self, request, conversation_id, *args, **kwargs):
        conversation = get_conversation_ou_404(request.user, conversation_id)
        context = _messages_context(request, conversation, _limite_demandee(request))
        return render(request, self.template_name, context)


class MessageSendView(LoginRequiredMixin, View):
    def post(self, request, conversation_id, *args, **kwargs):
        conversation = get_conversation_ou_404(request.user, conversation_id)
        contenu = request.POST.get('contenu', '').strip()

        if contenu:
            reponse_a = None
            reponse_a_id = request.POST.get('reponse_a', '').strip()
            if reponse_a_id:
                reponse_a = conversation.messages.filter(pk=reponse_a_id).first()
            envoyer_message(conversation, request.user, contenu, reponse_a=reponse_a)

        return redirect('messaging:conversation-detail', conversation_id=conversation.id)


class MessageAttachmentSendView(LoginRequiredMixin, View):
    """Upload d'une piece jointe (image/video/document/vocal — voir
    apps.messaging.attachments). Repond en JSON (pas de redirection) : le
    JS (realtime.js) suit la progression via XHR puis rafraichit le fragment
    de messages lui-meme, il n'a pas besoin d'un rendu HTML complet ici."""

    def post(self, request, conversation_id, *args, **kwargs):
        conversation = get_conversation_ou_404(request.user, conversation_id)
        uploaded_file = request.FILES.get('fichier')
        if uploaded_file is None:
            return JsonResponse({'success': False, 'error': "Aucun fichier reçu."}, status=400)

        contenu = request.POST.get('contenu', '').strip()
        duree_secondes = None
        if request.POST.get('duree_secondes', '').isdigit():
            duree_secondes = int(request.POST['duree_secondes'])

        try:
            message = envoyer_message_avec_fichier(
                conversation, request.user, uploaded_file, contenu, duree_secondes=duree_secondes,
            )
        except FichierInvalide as exc:
            return JsonResponse({'success': False, 'error': str(exc)}, status=400)

        return JsonResponse({'success': True, 'message_id': str(message.id)})


class MessageEditView(LoginRequiredMixin, View):
    def post(self, request, message_id, *args, **kwargs):
        message = get_message_ou_404(request.user, message_id)
        if message.auteur_id != request.user.id:
            raise PermissionDenied("Seul l'auteur peut modifier ce message.")

        contenu = request.POST.get('contenu', '').strip()
        if contenu and not message.est_supprime:
            modifier_message(message, contenu)

        return redirect('messaging:conversation-detail', conversation_id=message.conversation_id)


class MessageDeleteView(LoginRequiredMixin, View):
    def post(self, request, message_id, *args, **kwargs):
        message = get_message_ou_404(request.user, message_id)
        if message.auteur_id != request.user.id:
            raise PermissionDenied("Seul l'auteur peut supprimer ce message.")

        supprimer_message(message)
        return redirect('messaging:conversation-detail', conversation_id=message.conversation_id)


class AttachmentDownloadView(LoginRequiredMixin, View):
    """Seul point d'acces aux fichiers de messagerie : /medias/messaging/
    est exclu du serve public (voir config/urls.py). `?miniature=1` sert la
    version reduite (grille "Fichiers partages") quand elle existe, sinon
    retombe sur le fichier original."""

    def get(self, request, attachment_id, *args, **kwargs):
        attachment = get_attachment_ou_404(request.user, attachment_id)
        veut_miniature = request.GET.get('miniature') == '1' and attachment.miniature
        fichier = attachment.miniature if veut_miniature else attachment.fichier
        nom = attachment.nom_original or fichier.name.rsplit('/', 1)[-1]
        return FileResponse(fichier.open('rb'), filename=nom)
