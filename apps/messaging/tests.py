"""
apps/messaging/tests.py
Tests des permissions d'acces aux conversations et aux pieces jointes
(voir apps.messaging.permissions) : c'est le coeur de la Phase 2.
"""
import io
import shutil
import tempfile
import uuid

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.conteneurs.models import Dossier
from apps.notification.models import Notification
from apps.referentiels.models import (
    POD, POL, CompagnieMaritime, Commodite, Pays, SiteEmpotage, SiteSelection,
)
from apps.users.models import Agent_empotage, Agent_selection, Client, Personnel, Users

from . import services
from .attachments import FichierInvalide, TAILLE_MAX_OCTETS, valider_fichier
from .consumers import ConversationConsumer
from .models import Conversation, ConversationMember, Group, Message, MessageAttachment, MessageRead
from .services import MESSAGES_PAR_PAGE


def creer_referentiels(suffixe='1'):
    pays = Pays.objects.create(nom=f"Pays Test {suffixe}")
    return {
        'pays': pays,
        'pod': POD.objects.create(nom=f'POD {suffixe}', lieu='Port', Id_Pays=pays),
        'pol': POL.objects.create(nom=f'POL {suffixe}', lieu='Port', Id_Pays=pays),
        'commodite': Commodite.objects.create(nom=f'Commodite {suffixe}', Id_Pays=pays),
        'compagnie': CompagnieMaritime.objects.create(nom=f'Compagnie {suffixe}', lieu='Anvers', Id_Pays=pays),
        'site_selection': SiteSelection.objects.create(
            nom=f'Site S {suffixe}', contact='0000', lieu='Abidjan', Id_Pays=pays,
        ),
        'site_empotage': SiteEmpotage.objects.create(
            nom=f'Site E {suffixe}', contact='0000', lieu='Abidjan', Id_Pays=pays,
        ),
    }


def creer_user(username, user_type):
    user = Users.objects.create(username=username, email=f'{username}@test.local', user_type=user_type, is_active=True)
    user.set_password('1234')
    user.save()
    return user


def creer_dossier(ref, client_user, agent_selection_user, agent_empotage_user, personnel_user, trd):
    # get_or_create : ces wrappers sont OneToOne sur Users, et les tests
    # reutilisent parfois le meme agent/personnel sur plusieurs dossiers.
    client, _ = Client.objects.get_or_create(user=client_user)
    agent_selection, _ = Agent_selection.objects.get_or_create(user=agent_selection_user)
    agent_empotage, _ = Agent_empotage.objects.get_or_create(user=agent_empotage_user)
    personnel, _ = Personnel.objects.get_or_create(user=personnel_user)
    return Dossier.objects.create(
        TRD=trd, projet='Projet test', Booking='BK-1', type_conteneur='20_pieds',
        Id_Pays=ref['pays'], Id_POD=ref['pod'], Id_POL=ref['pol'],
        Id_Commodite=ref['commodite'], Id_CompagnieMaritime=ref['compagnie'],
        Id_SiteSelection=ref['site_selection'], Id_SiteEmpotage=ref['site_empotage'],
        Id_Agent_selection=agent_selection, Id_Agent_empotage=agent_empotage,
        id_client=client, Id_Personnel=personnel,
    )


class ConversationAccessTests(TestCase):
    def setUp(self):
        ref = creer_referentiels('1')
        self.client_user = creer_user('client1', 'client')
        self.agent_selection_user = creer_user('agent_sel1', 'agent_selection')
        self.agent_empotage_user = creer_user('agent_emp1', 'agent_empotage')
        self.personnel_user = creer_user('personnel1', 'personnel')
        self.etranger = creer_user('etranger', 'client')  # jamais rattache a aucun dossier

        self.dossier = creer_dossier(
            ref, self.client_user, self.agent_selection_user,
            self.agent_empotage_user, self.personnel_user, trd='TRD-TEST-001',
        )
        self.conversation = Conversation.objects.get(
            dossier=self.dossier, type_conversation=Conversation.TYPE_DOSSIER,
        )

    def test_membre_peut_acceder_a_la_conversation(self):
        self.client.login(username='client1', password='1234')
        url = reverse('messaging:conversation-detail', args=[self.conversation.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.dossier.TRD)

    def test_tous_les_roles_du_dossier_sont_membres(self):
        for username in ('client1', 'agent_sel1', 'agent_emp1', 'personnel1'):
            self.client.login(username=username, password='1234')
            url = reverse('messaging:conversation-detail', args=[self.conversation.id])
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"{username} devrait avoir acces")
            self.client.logout()

    def test_non_membre_recoit_404_pas_403(self):
        self.client.login(username='etranger', password='1234')
        url = reverse('messaging:conversation-detail', args=[self.conversation.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_anonyme_redirige_vers_login(self):
        url = reverse('messaging:conversation-detail', args=[self.conversation.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_liste_filtree_par_membre(self):
        ref2 = creer_referentiels('2')
        autre_client = creer_user('client2', 'client')
        creer_dossier(
            ref2, autre_client, self.agent_selection_user,
            self.agent_empotage_user, self.personnel_user, trd='TRD-TEST-002',
        )

        self.client.login(username='client1', password='1234')
        response = self.client.get(reverse('messaging:conversation-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TRD-TEST-001')
        self.assertNotContains(response, 'TRD-TEST-002')  # dossier d'un autre client

    def test_id_enumeration_conversation_inexistante(self):
        """Deviner un autre UUID dans l'URL ne doit jamais lever d'erreur
        serveur, juste un 404 propre (pas d'IDOR)."""
        self.client.login(username='client1', password='1234')
        url = reverse('messaging:conversation-detail', args=[uuid.uuid4()])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class AttachmentAccessTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        ref = creer_referentiels('3')
        self.client_user = creer_user('client3', 'client')
        self.agent_selection_user = creer_user('agent_sel3', 'agent_selection')
        self.agent_empotage_user = creer_user('agent_emp3', 'agent_empotage')
        self.personnel_user = creer_user('personnel3', 'personnel')
        self.etranger = creer_user('etranger3', 'client')

        self.dossier = creer_dossier(
            ref, self.client_user, self.agent_selection_user,
            self.agent_empotage_user, self.personnel_user, trd='TRD-TEST-003',
        )
        self.conversation = Conversation.objects.get(
            dossier=self.dossier, type_conversation=Conversation.TYPE_DOSSIER,
        )
        self.message = Message.objects.create(
            conversation=self.conversation, auteur=self.personnel_user,
            type_message=Message.TYPE_DOCUMENT, contenu='',
        )
        self.attachment = MessageAttachment.objects.create(
            message=self.message, type_fichier=MessageAttachment.TYPE_DOCUMENT,
            fichier=SimpleUploadedFile('rapport.pdf', b'%PDF-1.4 contenu test', content_type='application/pdf'),
            nom_original='rapport.pdf',
        )

    def test_membre_peut_telecharger(self):
        self.client.login(username='client3', password='1234')
        url = reverse('messaging:attachment-download', args=[self.attachment.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_non_membre_ne_peut_pas_telecharger(self):
        self.client.login(username='etranger3', password='1234')
        url = reverse('messaging:attachment-download', args=[self.attachment.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_medias_messaging_non_servi_publiquement(self):
        """/medias/messaging/... ne doit jamais repondre directement, meme
        sans authentification (voir config/urls.py)."""
        response = self.client.get(f'/medias/{self.attachment.fichier.name}')
        self.assertEqual(response.status_code, 404)


class MessageFlowTests(TestCase):
    """Phase 4 : envoi, edition, suppression, pagination, lecture, notifications."""

    def setUp(self):
        ref = creer_referentiels('4')
        self.client_user = creer_user('client4', 'client')
        self.agent_selection_user = creer_user('agent_sel4', 'agent_selection')
        self.agent_empotage_user = creer_user('agent_emp4', 'agent_empotage')
        self.personnel_user = creer_user('personnel4', 'personnel')
        self.etranger = creer_user('etranger4', 'client')

        self.dossier = creer_dossier(
            ref, self.client_user, self.agent_selection_user,
            self.agent_empotage_user, self.personnel_user, trd='TRD-TEST-004',
        )
        self.conversation = Conversation.objects.get(
            dossier=self.dossier, type_conversation=Conversation.TYPE_DOSSIER,
        )

    def test_membre_peut_envoyer_message(self):
        self.client.login(username='client4', password='1234')
        url = reverse('messaging:message-envoyer', args=[self.conversation.id])
        response = self.client.post(url, {'contenu': 'Bonjour, où en est le dossier ?'})
        self.assertRedirects(response, reverse('messaging:conversation-detail', args=[self.conversation.id]))

        message = Message.objects.get(conversation=self.conversation)
        self.assertEqual(message.auteur, self.client_user)
        self.assertEqual(message.type_message, Message.TYPE_TEXTE)
        self.assertEqual(message.contenu, 'Bonjour, où en est le dossier ?')

    def test_message_avec_emoji_est_conserve_et_affiche(self):
        self.client.login(username='client4', password='1234')
        url = reverse('messaging:message-envoyer', args=[self.conversation.id])
        contenu = 'Bien reçu 👍 merci ! 😀🎉'
        self.client.post(url, {'contenu': contenu})

        message = Message.objects.get(conversation=self.conversation)
        self.assertEqual(message.contenu, contenu)

        response = self.client.get(reverse('messaging:conversation-detail', args=[self.conversation.id]))
        self.assertContains(response, contenu)

    def test_envoi_message_met_a_jour_activite_conversation(self):
        ancienne_date = self.conversation.date_modifier
        self.client.login(username='client4', password='1234')
        self.client.post(
            reverse('messaging:message-envoyer', args=[self.conversation.id]),
            {'contenu': 'Un message'},
        )
        self.conversation.refresh_from_db()
        self.assertGreater(self.conversation.date_modifier, ancienne_date)

    def test_message_vide_est_ignore(self):
        self.client.login(username='client4', password='1234')
        self.client.post(reverse('messaging:message-envoyer', args=[self.conversation.id]), {'contenu': '   '})
        self.assertEqual(Message.objects.filter(conversation=self.conversation).count(), 0)

    def test_non_membre_ne_peut_pas_envoyer(self):
        self.client.login(username='etranger4', password='1234')
        url = reverse('messaging:message-envoyer', args=[self.conversation.id])
        response = self.client.post(url, {'contenu': 'Je ne devrais pas pouvoir'})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Message.objects.filter(conversation=self.conversation).count(), 0)

    def test_envoi_notifie_les_autres_membres_pas_lauteur(self):
        self.client.login(username='client4', password='1234')
        self.client.post(
            reverse('messaging:message-envoyer', args=[self.conversation.id]),
            {'contenu': 'Le conteneur est arrivé.'},
        )
        notifs = Notification.objects.filter(type_notification=Notification.TYPE_NOUVEAU_MESSAGE)
        destinataires = set(notifs.values_list('user_id', flat=True))
        self.assertIn(self.agent_selection_user.id, destinataires)
        self.assertIn(self.agent_empotage_user.id, destinataires)
        self.assertIn(self.personnel_user.id, destinataires)
        self.assertNotIn(self.client_user.id, destinataires)  # l'auteur n'est pas notifie de son propre message

    def test_auteur_peut_modifier_son_message(self):
        self.client.login(username='client4', password='1234')
        self.client.post(
            reverse('messaging:message-envoyer', args=[self.conversation.id]), {'contenu': 'Version 1'},
        )
        message = Message.objects.get(conversation=self.conversation)

        response = self.client.post(
            reverse('messaging:message-modifier', args=[message.id]), {'contenu': 'Version corrigée'},
        )
        self.assertRedirects(response, reverse('messaging:conversation-detail', args=[self.conversation.id]))
        message.refresh_from_db()
        self.assertEqual(message.contenu, 'Version corrigée')

    def test_non_auteur_ne_peut_pas_modifier(self):
        self.client.login(username='client4', password='1234')
        self.client.post(
            reverse('messaging:message-envoyer', args=[self.conversation.id]), {'contenu': 'Original'},
        )
        message = Message.objects.get(conversation=self.conversation)

        self.client.logout()
        self.client.login(username='personnel4', password='1234')  # membre legitime, mais pas l'auteur
        response = self.client.post(
            reverse('messaging:message-modifier', args=[message.id]), {'contenu': 'Modifie par un autre'},
        )
        self.assertEqual(response.status_code, 403)
        message.refresh_from_db()
        self.assertEqual(message.contenu, 'Original')

    def test_non_membre_ne_peut_pas_modifier(self):
        self.client.login(username='client4', password='1234')
        self.client.post(
            reverse('messaging:message-envoyer', args=[self.conversation.id]), {'contenu': 'Original'},
        )
        message = Message.objects.get(conversation=self.conversation)

        self.client.logout()
        self.client.login(username='etranger4', password='1234')
        response = self.client.post(
            reverse('messaging:message-modifier', args=[message.id]), {'contenu': 'Intrus'},
        )
        self.assertEqual(response.status_code, 404)

    def test_auteur_peut_supprimer_son_message_soft_delete(self):
        self.client.login(username='client4', password='1234')
        self.client.post(
            reverse('messaging:message-envoyer', args=[self.conversation.id]), {'contenu': 'A supprimer'},
        )
        message = Message.objects.get(conversation=self.conversation)

        response = self.client.post(reverse('messaging:message-supprimer', args=[message.id]))
        self.assertRedirects(response, reverse('messaging:conversation-detail', args=[self.conversation.id]))
        message.refresh_from_db()
        self.assertTrue(message.est_supprime)
        self.assertEqual(message.contenu, 'A supprimer')  # soft delete : le contenu reste en base

    def test_non_auteur_ne_peut_pas_supprimer(self):
        self.client.login(username='client4', password='1234')
        self.client.post(
            reverse('messaging:message-envoyer', args=[self.conversation.id]), {'contenu': 'Original'},
        )
        message = Message.objects.get(conversation=self.conversation)

        self.client.logout()
        self.client.login(username='personnel4', password='1234')
        response = self.client.post(reverse('messaging:message-supprimer', args=[message.id]))
        self.assertEqual(response.status_code, 403)
        message.refresh_from_db()
        self.assertFalse(message.est_supprime)

    def test_ouverture_conversation_marque_les_messages_comme_lus(self):
        self.client.login(username='personnel4', password='1234')
        self.client.post(
            reverse('messaging:message-envoyer', args=[self.conversation.id]), {'contenu': 'Message du personnel'},
        )
        message = Message.objects.get(conversation=self.conversation)
        self.client.logout()

        self.client.login(username='client4', password='1234')
        self.client.get(reverse('messaging:conversation-detail', args=[self.conversation.id]))

        self.assertTrue(MessageRead.objects.filter(message=message, user=self.client_user).exists())
        membre = ConversationMember.objects.get(conversation=self.conversation, user=self.client_user)
        self.assertEqual(membre.dernier_message_lu_id, message.id)
        self.assertIsNotNone(membre.date_dernier_lu)

    def test_pagination_ne_charge_pas_tout_par_defaut(self):
        for i in range(MESSAGES_PAR_PAGE + 10):
            Message.objects.create(
                conversation=self.conversation, auteur=self.personnel_user,
                type_message=Message.TYPE_TEXTE, contenu=f'Message {i}',
            )

        self.client.login(username='client4', password='1234')
        response = self.client.get(reverse('messaging:conversation-detail', args=[self.conversation.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['messages_conversation']), MESSAGES_PAR_PAGE)
        self.assertTrue(response.context['a_plus_anciens'])
        self.assertContains(response, 'Charger les messages précédents')

    def test_pagination_limite_parametre_charge_plus(self):
        for i in range(MESSAGES_PAR_PAGE + 10):
            Message.objects.create(
                conversation=self.conversation, auteur=self.personnel_user,
                type_message=Message.TYPE_TEXTE, contenu=f'Message {i}',
            )

        self.client.login(username='client4', password='1234')
        url = reverse('messaging:conversation-detail', args=[self.conversation.id])
        response = self.client.get(url, {'limite': MESSAGES_PAR_PAGE * 2})
        self.assertEqual(len(response.context['messages_conversation']), MESSAGES_PAR_PAGE + 10)
        self.assertFalse(response.context['a_plus_anciens'])

    def test_affichage_message_dont_lauteur_a_ete_supprime(self):
        """Regression : Message.auteur est SET_NULL. Un message dont l'auteur
        n'existe plus (compte supprime) ne doit jamais faire planter le
        rendu (VariableDoesNotExist sur un argument de filtre chaine) —
        observe en conditions reelles avec un message reste en base apres
        suppression de son auteur."""
        Message.objects.create(
            conversation=self.conversation, auteur=None,
            type_message=Message.TYPE_TEXTE, contenu='Message orphelin',
        )
        self.client.login(username='client4', password='1234')
        response = self.client.get(reverse('messaging:conversation-detail', args=[self.conversation.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Utilisateur supprimé')
        self.assertContains(response, 'Message orphelin')


def _scope_pour(conversation, user):
    """Scope minimal pour tester le consumer directement (sans passer par
    AuthMiddlewareStack/URLRouter, cf. doc Channels sur les tests de
    consumers) : on injecte `user` et `url_route` a la main."""
    return {'user': user, 'url_route': {'kwargs': {'conversation_id': str(conversation.id)}}}


class ConsumerTests(TransactionTestCase):
    """Phase 5 : securite et diffusion du WebSocket temps reel.

    TransactionTestCase (pas TestCase) : le consumer WebSocket execute les
    acces base de donnees dans un thread separe (mecanisme sync-to-async de
    Channels), ce qui ne cohabite pas avec la transaction/savepoint unique
    de TestCase — cf. doc Channels sur le test des consumers."""

    def setUp(self):
        ref = creer_referentiels('5')
        self.client_user = creer_user('client5', 'client')
        self.agent_selection_user = creer_user('agent_sel5', 'agent_selection')
        self.agent_empotage_user = creer_user('agent_emp5', 'agent_empotage')
        self.personnel_user = creer_user('personnel5', 'personnel')
        self.etranger = creer_user('etranger5', 'client')

        self.dossier = creer_dossier(
            ref, self.client_user, self.agent_selection_user,
            self.agent_empotage_user, self.personnel_user, trd='TRD-TEST-005',
        )
        self.conversation = Conversation.objects.get(
            dossier=self.dossier, type_conversation=Conversation.TYPE_DOSSIER,
        )

    async def test_membre_peut_se_connecter(self):
        communicator = WebsocketCommunicator(ConversationConsumer.as_asgi(), '/ws/test/')
        communicator.scope.update(_scope_pour(self.conversation, self.client_user))
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_non_membre_est_rejete(self):
        communicator = WebsocketCommunicator(ConversationConsumer.as_asgi(), '/ws/test/')
        communicator.scope.update(_scope_pour(self.conversation, self.etranger))
        connected, subprotocol_ou_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(subprotocol_ou_code, 4004)

    async def test_anonyme_est_rejete(self):
        communicator = WebsocketCommunicator(ConversationConsumer.as_asgi(), '/ws/test/')
        communicator.scope.update(_scope_pour(self.conversation, AnonymousUser()))
        connected, subprotocol_ou_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(subprotocol_ou_code, 4001)

    async def test_nouveau_message_est_diffuse_aux_membres_connectes(self):
        com_client = WebsocketCommunicator(ConversationConsumer.as_asgi(), '/ws/test/')
        com_client.scope.update(_scope_pour(self.conversation, self.client_user))
        com_personnel = WebsocketCommunicator(ConversationConsumer.as_asgi(), '/ws/test/')
        com_personnel.scope.update(_scope_pour(self.conversation, self.personnel_user))

        self.assertTrue((await com_client.connect())[0])
        self.assertTrue((await com_personnel.connect())[0])

        await database_sync_to_async(services.envoyer_message)(
            self.conversation, self.agent_selection_user, 'Bonjour a tous',
        )

        self.assertEqual(await com_client.receive_json_from(), {'type': 'nouveau_message'})
        self.assertEqual(await com_personnel.receive_json_from(), {'type': 'nouveau_message'})

        await com_client.disconnect()
        await com_personnel.disconnect()

    async def test_typing_est_relaye_aux_autres_mais_pas_a_soi(self):
        com_a = WebsocketCommunicator(ConversationConsumer.as_asgi(), '/ws/test/')
        com_a.scope.update(_scope_pour(self.conversation, self.client_user))
        com_b = WebsocketCommunicator(ConversationConsumer.as_asgi(), '/ws/test/')
        com_b.scope.update(_scope_pour(self.conversation, self.personnel_user))

        self.assertTrue((await com_a.connect())[0])
        self.assertTrue((await com_b.connect())[0])

        await com_a.send_json_to({'type': 'typing', 'typing': True})

        evenement = await com_b.receive_json_from()
        self.assertEqual(evenement['type'], 'typing')
        self.assertTrue(evenement['typing'])
        self.assertEqual(evenement['user_id'], self.client_user.id)

        self.assertTrue(await com_a.receive_nothing())  # pas d'echo a soi-meme

        await com_a.disconnect()
        await com_b.disconnect()


def _image_valide(nom='photo.jpg', taille=(20, 20), format_pil='JPEG', content_type='image/jpeg'):
    buffer = io.BytesIO()
    Image.new('RGB', taille, (200, 30, 30)).save(buffer, format=format_pil)
    buffer.seek(0)
    return SimpleUploadedFile(nom, buffer.read(), content_type=content_type)


class _TailleSeule:
    """Objet minimal (content_type + size) pour tester le rejet par taille
    sans allouer de vrais octets — valider_fichier() ne lit le contenu que
    pour la categorie image."""
    def __init__(self, content_type, size):
        self.content_type = content_type
        self.size = size


class AttachmentValidationTests(TestCase):
    """Phase 6 : validation des pieces jointes (apps.messaging.attachments)."""

    def test_image_valide_est_acceptee(self):
        categorie = valider_fichier(_image_valide())
        self.assertEqual(categorie, 'image')

    def test_document_pdf_valide_est_accepte(self):
        fichier = SimpleUploadedFile('rapport.pdf', b'%PDF-1.4 contenu', content_type='application/pdf')
        categorie = valider_fichier(fichier)
        self.assertEqual(categorie, 'document')

    def test_type_non_autorise_est_rejete(self):
        fichier = SimpleUploadedFile('virus.exe', b'MZ...', content_type='application/x-msdownload')
        with self.assertRaises(FichierInvalide):
            valider_fichier(fichier)

    def test_fausse_image_est_rejetee(self):
        """Content-Type declare 'image/jpeg' mais le contenu n'est pas une
        image reelle — la verification de contenu doit rejeter, pas se fier
        au seul en-tete (facilement falsifiable)."""
        fichier = SimpleUploadedFile('faux.jpg', b'ceci n\'est pas une image', content_type='image/jpeg')
        with self.assertRaises(FichierInvalide):
            valider_fichier(fichier)

    def test_document_trop_volumineux_est_rejete(self):
        limite = TAILLE_MAX_OCTETS['document']
        fichier = _TailleSeule('application/pdf', limite + 1)
        with self.assertRaises(FichierInvalide):
            valider_fichier(fichier)

    def test_document_a_la_limite_est_accepte(self):
        limite = TAILLE_MAX_OCTETS['document']
        fichier = _TailleSeule('application/pdf', limite)
        self.assertEqual(valider_fichier(fichier), 'document')


TEMP_MEDIA_ROOT_P6 = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT_P6)
class AttachmentUploadViewTests(TestCase):
    """Phase 6 : upload de pieces jointes via MessageAttachmentSendView."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT_P6, ignore_errors=True)

    def setUp(self):
        ref = creer_referentiels('6')
        self.client_user = creer_user('client6', 'client')
        self.agent_selection_user = creer_user('agent_sel6', 'agent_selection')
        self.agent_empotage_user = creer_user('agent_emp6', 'agent_empotage')
        self.personnel_user = creer_user('personnel6', 'personnel')
        self.etranger = creer_user('etranger6', 'client')

        self.dossier = creer_dossier(
            ref, self.client_user, self.agent_selection_user,
            self.agent_empotage_user, self.personnel_user, trd='TRD-TEST-006',
        )
        self.conversation = Conversation.objects.get(
            dossier=self.dossier, type_conversation=Conversation.TYPE_DOSSIER,
        )

    def test_membre_peut_envoyer_une_image(self):
        self.client.login(username='client6', password='1234')
        url = reverse('messaging:message-envoyer-fichier', args=[self.conversation.id])
        response = self.client.post(url, {'fichier': _image_valide()})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        message = Message.objects.get(conversation=self.conversation)
        self.assertEqual(message.type_message, 'image')
        piece = message.pieces_jointes.get()
        self.assertEqual(piece.type_fichier, 'image')
        self.assertTrue(piece.fichier.name.endswith('.webp'))  # converti (compression)
        self.assertIsNotNone(piece.miniature)

    def test_caption_est_conservee_avec_le_fichier(self):
        self.client.login(username='client6', password='1234')
        url = reverse('messaging:message-envoyer-fichier', args=[self.conversation.id])
        response = self.client.post(url, {'fichier': _image_valide(), 'contenu': 'Voici le conteneur'})
        self.assertEqual(response.status_code, 200)
        message = Message.objects.get(conversation=self.conversation)
        self.assertEqual(message.contenu, 'Voici le conteneur')

    def test_non_membre_ne_peut_pas_envoyer_fichier(self):
        self.client.login(username='etranger6', password='1234')
        url = reverse('messaging:message-envoyer-fichier', args=[self.conversation.id])
        response = self.client.post(url, {'fichier': _image_valide()})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Message.objects.filter(conversation=self.conversation).exists())

    def test_fichier_invalide_renvoie_erreur_sans_rien_enregistrer(self):
        self.client.login(username='client6', password='1234')
        url = reverse('messaging:message-envoyer-fichier', args=[self.conversation.id])
        fichier = SimpleUploadedFile('virus.exe', b'MZ...', content_type='application/x-msdownload')
        response = self.client.post(url, {'fichier': fichier})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertFalse(Message.objects.filter(conversation=self.conversation).exists())
        self.assertFalse(MessageAttachment.objects.exists())

    def test_telechargement_original_reserve_aux_membres(self):
        self.client.login(username='client6', password='1234')
        url = reverse('messaging:message-envoyer-fichier', args=[self.conversation.id])
        self.client.post(url, {'fichier': _image_valide()})
        piece = MessageAttachment.objects.get()

        dl_url = reverse('messaging:attachment-download', args=[piece.id])

        self.client.logout()
        self.client.login(username='etranger6', password='1234')
        self.assertEqual(self.client.get(dl_url).status_code, 404)

        self.client.logout()
        self.client.login(username='client6', password='1234')
        self.assertEqual(self.client.get(dl_url).status_code, 200)
        self.assertEqual(self.client.get(dl_url + '?miniature=1').status_code, 200)

    def test_fichiers_partages_apparait_dans_le_detail(self):
        self.client.login(username='client6', password='1234')
        self.client.post(
            reverse('messaging:message-envoyer-fichier', args=[self.conversation.id]),
            {'fichier': _image_valide(nom='conteneur.jpg')},
        )
        response = self.client.get(reverse('messaging:conversation-detail', args=[self.conversation.id]))
        self.assertContains(response, 'Fichiers partagés')
        self.assertContains(response, 'miniature=1')


def _vocal_valide(nom='vocal.webm', content_type='audio/webm;codecs=opus'):
    return SimpleUploadedFile(nom, b'faux contenu audio webm', content_type=content_type)


class VoiceMessageValidationTests(TestCase):
    """Phase 7 : validation des vocaux (apps.messaging.attachments)."""

    def test_vocal_webm_avec_codec_est_accepte(self):
        """Le Content-Type d'un blob MediaRecorder inclut souvent le codec
        (ex. 'audio/webm;codecs=opus') : la validation ne doit comparer que
        le type de base, pas rejeter a cause du parametre."""
        categorie = valider_fichier(_vocal_valide())
        self.assertEqual(categorie, 'audio')

    def test_vocal_trop_volumineux_est_rejete(self):
        limite = TAILLE_MAX_OCTETS['audio']
        fichier = _TailleSeule('audio/webm', limite + 1)
        with self.assertRaises(FichierInvalide):
            valider_fichier(fichier)


TEMP_MEDIA_ROOT_P7 = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT_P7)
class VoiceMessageUploadTests(TestCase):
    """Phase 7 : envoi d'un message vocal via MessageAttachmentSendView."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT_P7, ignore_errors=True)

    def setUp(self):
        ref = creer_referentiels('7')
        self.client_user = creer_user('client7', 'client')
        self.agent_selection_user = creer_user('agent_sel7', 'agent_selection')
        self.agent_empotage_user = creer_user('agent_emp7', 'agent_empotage')
        self.personnel_user = creer_user('personnel7', 'personnel')

        self.dossier = creer_dossier(
            ref, self.client_user, self.agent_selection_user,
            self.agent_empotage_user, self.personnel_user, trd='TRD-TEST-007',
        )
        self.conversation = Conversation.objects.get(
            dossier=self.dossier, type_conversation=Conversation.TYPE_DOSSIER,
        )

    def test_membre_peut_envoyer_un_vocal_avec_duree(self):
        self.client.login(username='client7', password='1234')
        url = reverse('messaging:message-envoyer-fichier', args=[self.conversation.id])
        response = self.client.post(url, {'fichier': _vocal_valide(), 'duree_secondes': '17'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        message = Message.objects.get(conversation=self.conversation)
        self.assertEqual(message.type_message, 'audio')
        piece = message.pieces_jointes.get()
        self.assertEqual(piece.type_fichier, 'audio')
        self.assertEqual(piece.duree_secondes, 17)

    def test_duree_ignoree_pour_un_fichier_non_audio(self):
        self.client.login(username='client7', password='1234')
        url = reverse('messaging:message-envoyer-fichier', args=[self.conversation.id])
        # duree_secondes envoyee par erreur sur un upload d'image : ne doit
        # jamais se retrouver sur une piece jointe qui n'est pas un vocal.
        response = self.client.post(url, {'fichier': _image_valide(), 'duree_secondes': '99'})
        self.assertEqual(response.status_code, 200)
        piece = MessageAttachment.objects.get()
        self.assertEqual(piece.type_fichier, 'image')
        self.assertIsNone(piece.duree_secondes)

    def test_vocal_sans_duree_est_accepte(self):
        self.client.login(username='client7', password='1234')
        url = reverse('messaging:message-envoyer-fichier', args=[self.conversation.id])
        response = self.client.post(url, {'fichier': _vocal_valide()})
        self.assertEqual(response.status_code, 200)
        piece = MessageAttachment.objects.get()
        self.assertIsNone(piece.duree_secondes)

    def test_lecteur_audio_et_section_vocaux_dans_le_detail(self):
        self.client.login(username='client7', password='1234')
        self.client.post(
            reverse('messaging:message-envoyer-fichier', args=[self.conversation.id]),
            {'fichier': _vocal_valide(), 'duree_secondes': '5'},
        )
        response = self.client.get(reverse('messaging:conversation-detail', args=[self.conversation.id]))
        self.assertContains(response, '<audio')
        self.assertContains(response, 'Vocaux')
        self.assertContains(response, '0:05')


class PrivateConversationServiceTests(TestCase):
    """Phase 8 : services.get_or_create_conversation_privee."""

    def setUp(self):
        self.alice = creer_user('alice8', 'personnel')
        self.bob = creer_user('bob8', 'client')

    def test_cree_une_conversation_privee_avec_deux_membres(self):
        conversation = services.get_or_create_conversation_privee(self.alice, self.bob)
        self.assertEqual(conversation.type_conversation, Conversation.TYPE_PRIVEE)
        membres = set(conversation.membres_conversation.values_list('user_id', flat=True))
        self.assertEqual(membres, {self.alice.id, self.bob.id})

    def test_reutilise_la_conversation_existante_meme_paire(self):
        premiere = services.get_or_create_conversation_privee(self.alice, self.bob)
        deuxieme = services.get_or_create_conversation_privee(self.alice, self.bob)
        self.assertEqual(premiere.id, deuxieme.id)
        self.assertEqual(Conversation.objects.filter(type_conversation=Conversation.TYPE_PRIVEE).count(), 1)

    def test_reutilise_la_conversation_existante_ordre_inverse(self):
        premiere = services.get_or_create_conversation_privee(self.alice, self.bob)
        deuxieme = services.get_or_create_conversation_privee(self.bob, self.alice)
        self.assertEqual(premiere.id, deuxieme.id)

    def test_rejette_une_conversation_avec_soi_meme(self):
        with self.assertRaises(ValueError):
            services.get_or_create_conversation_privee(self.alice, self.alice)


class PrivateConversationViewTests(TestCase):
    """Phase 8 : annuaire + demarrage de conversation privee."""

    def setUp(self):
        self.alice = creer_user('alice8b', 'personnel')
        self.bob = creer_user('bob8b', 'client')
        self.carole = creer_user('carole8b', 'agent_selection')
        self.inactif = creer_user('inactif8b', 'client')
        self.inactif.is_active = False
        self.inactif.save(update_fields=['is_active'])

    def test_annuaire_liste_les_utilisateurs_actifs_sauf_soi_meme(self):
        self.client.login(username='alice8b', password='1234')
        response = self.client.get(reverse('messaging:nouvelle-conversation'))
        self.assertEqual(response.status_code, 200)
        noms = {u.username for u in response.context['utilisateurs']}
        self.assertIn('bob8b', noms)
        self.assertIn('carole8b', noms)
        self.assertNotIn('alice8b', noms)  # jamais soi-meme
        self.assertNotIn('inactif8b', noms)  # jamais un compte desactive

    def test_annuaire_recherche_filtre_les_resultats(self):
        self.client.login(username='alice8b', password='1234')
        response = self.client.get(reverse('messaging:nouvelle-conversation'), {'q': 'carole8b'})
        noms = {u.username for u in response.context['utilisateurs']}
        self.assertEqual(noms, {'carole8b'})

    def test_demarrer_conversation_privee_cree_et_redirige(self):
        self.client.login(username='alice8b', password='1234')
        url = reverse('messaging:demarrer-conversation-privee', args=[self.bob.id])
        response = self.client.post(url)

        conversation = Conversation.objects.get(
            type_conversation=Conversation.TYPE_PRIVEE,
            membres_conversation__user=self.alice,
        )
        self.assertRedirects(response, reverse('messaging:conversation-detail', args=[conversation.id]))

    def test_demarrer_deux_fois_ne_duplique_pas(self):
        self.client.login(username='alice8b', password='1234')
        url = reverse('messaging:demarrer-conversation-privee', args=[self.bob.id])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(
            Conversation.objects.filter(
                type_conversation=Conversation.TYPE_PRIVEE, membres_conversation__user=self.alice,
            ).count(),
            1,
        )

    def test_ne_peut_pas_demarrer_avec_soi_meme(self):
        self.client.login(username='alice8b', password='1234')
        url = reverse('messaging:demarrer-conversation-privee', args=[self.alice.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_ne_peut_pas_demarrer_avec_un_compte_inactif(self):
        self.client.login(username='alice8b', password='1234')
        url = reverse('messaging:demarrer-conversation-privee', args=[self.inactif.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_tiers_ne_peut_pas_acceder_a_la_conversation_privee_dautrui(self):
        conversation = services.get_or_create_conversation_privee(self.alice, self.bob)
        self.client.login(username='carole8b', password='1234')
        response = self.client.get(reverse('messaging:conversation-detail', args=[conversation.id]))
        self.assertEqual(response.status_code, 404)

    def test_titre_affiche_est_le_nom_de_lautre_utilisateur(self):
        conversation = services.get_or_create_conversation_privee(self.alice, self.bob)
        self.client.login(username='alice8b', password='1234')
        response = self.client.get(reverse('messaging:conversation-detail', args=[conversation.id]))
        self.assertContains(response, 'bob8b')  # nom_affichage retombe sur le username sans prenom/nom


class GroupServiceTests(TestCase):
    """Phase 9 : services.creer_groupe / ajouter_membres_groupe / retirer_membre_groupe."""

    def setUp(self):
        self.alice = creer_user('alice9', 'personnel')
        self.bob = creer_user('bob9', 'client')
        self.carole = creer_user('carole9', 'agent_selection')

    def test_creer_groupe_le_createur_est_admin(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Test', membres=[self.bob])
        membre = ConversationMember.objects.get(conversation=groupe.conversation, user=self.alice)
        self.assertEqual(membre.role, ConversationMember.ROLE_ADMIN)

    def test_creer_groupe_les_membres_sont_ajoutes_en_role_membre(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Test', membres=[self.bob, self.carole])
        ids = set(groupe.conversation.membres_conversation.values_list('user_id', flat=True))
        self.assertEqual(ids, {self.alice.id, self.bob.id, self.carole.id})
        membre = ConversationMember.objects.get(conversation=groupe.conversation, user=self.bob)
        self.assertEqual(membre.role, ConversationMember.ROLE_MEMBRE)

    def test_creer_groupe_ignore_le_createur_meme_sil_est_dans_membres(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Test', membres=[self.alice, self.bob])
        self.assertEqual(groupe.conversation.membres_conversation.count(), 2)

    def test_creer_groupe_notifie_les_membres_ajoutes_pas_le_createur(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Test', membres=[self.bob])
        self.assertTrue(Notification.objects.filter(user=self.bob, type_notification=Notification.TYPE_AJOUT_GROUPE).exists())
        self.assertFalse(Notification.objects.filter(user=self.alice, type_notification=Notification.TYPE_AJOUT_GROUPE).exists())

    def test_creer_groupe_avec_dossier_associe(self):
        ref = creer_referentiels('9')
        dossier = creer_dossier(ref, self.bob, self.carole, self.alice, self.alice, trd='TRD-GRP-9')
        groupe = services.creer_groupe(self.alice, 'Equipe Dossier', dossier=dossier, membres=[self.bob])
        self.assertEqual(groupe.conversation.dossier_id, dossier.id)

    def test_ajouter_membres_ignore_un_deja_membre(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Test', membres=[self.bob])
        nouveaux = services.ajouter_membres_groupe(groupe, [self.bob, self.carole])
        self.assertEqual(nouveaux, [self.carole])
        self.assertEqual(groupe.conversation.membres_conversation.count(), 3)

    def test_ajouter_membres_notifie_seulement_les_nouveaux(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Test', membres=[self.bob])
        Notification.objects.all().delete()
        services.ajouter_membres_groupe(groupe, [self.bob, self.carole])
        self.assertFalse(Notification.objects.filter(user=self.bob).exists())
        self.assertTrue(Notification.objects.filter(user=self.carole, type_notification=Notification.TYPE_AJOUT_GROUPE).exists())

    def test_retirer_membre_simple(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Test', membres=[self.bob])
        services.retirer_membre_groupe(groupe, self.bob)
        self.assertFalse(
            ConversationMember.objects.filter(conversation=groupe.conversation, user=self.bob).exists()
        )

    def test_retirer_membre_non_admin_ne_promeut_personne(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Test', membres=[self.bob, self.carole])
        services.retirer_membre_groupe(groupe, self.bob)
        admins = ConversationMember.objects.filter(conversation=groupe.conversation, role=ConversationMember.ROLE_ADMIN)
        self.assertEqual(set(admins.values_list('user_id', flat=True)), {self.alice.id})

    def test_retirer_dernier_admin_promeut_le_membre_le_plus_ancien(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Test', membres=[self.bob, self.carole])
        services.retirer_membre_groupe(groupe, self.alice)
        membre = ConversationMember.objects.get(conversation=groupe.conversation, user=self.bob)
        self.assertEqual(membre.role, ConversationMember.ROLE_ADMIN)

    def test_retirer_le_seul_membre_restant_ne_plante_pas(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Solo')
        services.retirer_membre_groupe(groupe, self.alice)
        self.assertEqual(groupe.conversation.membres_conversation.count(), 0)


class GroupViewTests(TestCase):
    """Phase 9 : creation de groupe, gestion des membres (vues)."""

    def setUp(self):
        self.alice = creer_user('alice9v', 'personnel')
        self.bob = creer_user('bob9v', 'client')
        self.carole = creer_user('carole9v', 'agent_selection')
        self.etranger = creer_user('etranger9v', 'client')

    def test_creation_groupe_via_formulaire(self):
        self.client.login(username='alice9v', password='1234')
        url = reverse('messaging:nouveau-groupe')
        response = self.client.post(url, {
            'nom': 'Groupe Formulaire', 'description': 'Un groupe de test',
            'membres': [str(self.bob.id), str(self.carole.id)],
        })
        groupe = Group.objects.get(nom='Groupe Formulaire')
        self.assertRedirects(response, reverse('messaging:conversation-detail', args=[groupe.conversation_id]))
        ids = set(groupe.conversation.membres_conversation.values_list('user_id', flat=True))
        self.assertEqual(ids, {self.alice.id, self.bob.id, self.carole.id})
        self.assertEqual(
            ConversationMember.objects.get(conversation=groupe.conversation, user=self.alice).role,
            ConversationMember.ROLE_ADMIN,
        )

    def test_creation_groupe_sans_nom_ne_cree_rien(self):
        self.client.login(username='alice9v', password='1234')
        url = reverse('messaging:nouveau-groupe')
        response = self.client.post(url, {'nom': '  ', 'membres': [str(self.bob.id)]})
        self.assertRedirects(response, url)
        self.assertFalse(Group.objects.filter(cree_par=self.alice).exists())

    def test_ajout_membres_reserve_aux_admins(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Admin', membres=[self.bob])
        self.client.login(username='bob9v', password='1234')  # bob est membre mais pas admin
        url = reverse('messaging:groupe-ajouter-membres', args=[groupe.conversation_id])
        response = self.client.post(url, {'membres': [str(self.carole.id)]})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            ConversationMember.objects.filter(conversation=groupe.conversation, user=self.carole).exists()
        )

    def test_ajout_membres_par_un_admin_fonctionne(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Admin', membres=[self.bob])
        self.client.login(username='alice9v', password='1234')
        url = reverse('messaging:groupe-ajouter-membres', args=[groupe.conversation_id])
        response = self.client.post(url, {'membres': [str(self.carole.id)]})
        self.assertRedirects(response, reverse('messaging:conversation-detail', args=[groupe.conversation_id]))
        self.assertTrue(
            ConversationMember.objects.filter(conversation=groupe.conversation, user=self.carole).exists()
        )

    def test_ajout_membres_non_membre_recoit_404(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Admin', membres=[self.bob])
        self.client.login(username='etranger9v', password='1234')
        url = reverse('messaging:groupe-ajouter-membres', args=[groupe.conversation_id])
        response = self.client.post(url, {'membres': [str(self.carole.id)]})
        self.assertEqual(response.status_code, 404)

    def test_retrait_membre_reserve_aux_admins(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Admin', membres=[self.bob, self.carole])
        self.client.login(username='bob9v', password='1234')
        url = reverse('messaging:groupe-retirer-membre', args=[groupe.conversation_id, self.carole.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            ConversationMember.objects.filter(conversation=groupe.conversation, user=self.carole).exists()
        )

    def test_retrait_membre_par_un_admin_fonctionne(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Admin', membres=[self.bob, self.carole])
        self.client.login(username='alice9v', password='1234')
        url = reverse('messaging:groupe-retirer-membre', args=[groupe.conversation_id, self.carole.id])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('messaging:conversation-detail', args=[groupe.conversation_id]))
        self.assertFalse(
            ConversationMember.objects.filter(conversation=groupe.conversation, user=self.carole).exists()
        )

    def test_quitter_le_groupe_accessible_a_tout_membre(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Admin', membres=[self.bob])
        self.client.login(username='bob9v', password='1234')  # simple membre, pas admin
        url = reverse('messaging:groupe-quitter', args=[groupe.conversation_id])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('messaging:conversation-list'))
        self.assertFalse(
            ConversationMember.objects.filter(conversation=groupe.conversation, user=self.bob).exists()
        )

    def test_non_membre_ne_peut_pas_acceder_a_la_gestion_du_groupe(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Admin', membres=[self.bob])
        self.client.login(username='etranger9v', password='1234')
        url = reverse('messaging:groupe-ajouter-membres', args=[groupe.conversation_id])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_gestion_de_groupe_sur_conversation_privee_recoit_404(self):
        conversation = services.get_or_create_conversation_privee(self.alice, self.bob)
        self.client.login(username='alice9v', password='1234')
        url = reverse('messaging:groupe-quitter', args=[conversation.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_detail_du_groupe_affiche_les_controles_admin_uniquement_pour_ladmin(self):
        groupe = services.creer_groupe(self.alice, 'Equipe Visible', membres=[self.bob])
        url = reverse('messaging:conversation-detail', args=[groupe.conversation_id])

        self.client.login(username='alice9v', password='1234')
        response = self.client.get(url)
        self.assertContains(response, 'Ajouter des membres')

        self.client.logout()
        self.client.login(username='bob9v', password='1234')
        response = self.client.get(url)
        self.assertNotContains(response, 'Ajouter des membres')
        self.assertContains(response, 'Quitter le groupe')
