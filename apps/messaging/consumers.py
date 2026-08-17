"""
apps/messaging/consumers.py
WebSocket temps reel pour une conversation. Volontairement minimaliste : le
consumer ne sert qu'a (1) verifier qui a le droit d'ecouter, (2) relayer un
signal "typing" entre membres, et (3) notifier "quelque chose a change" pour
que le navigateur recharge le fragment HTML des messages (voir
static/messaging/js/realtime.js). Aucune logique metier ici — la creation
des messages reste sur MessageSendView/services.py (POST classique), seule
source de verite ; ca evite de dupliquer la validation et le rendu HTML des
messages en JS.
"""
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .permissions import conversations_visibles


class ConversationConsumer(JsonWebsocketConsumer):
    def connect(self):
        user = self.scope['user']
        conversation_id = self.scope['url_route']['kwargs']['conversation_id']

        if not user.is_authenticated:
            self.close(code=4001)
            return

        conversation = conversations_visibles(user).filter(pk=conversation_id).first()
        if conversation is None:
            # Jamais confirmer l'existence d'une conversation a un non-membre,
            # meme via le code de fermeture — meme motif que permissions.py.
            self.close(code=4004)
            return

        self.user = user
        self.group_name = f'conversation_{conversation_id}'
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        if getattr(self, 'group_name', None):
            async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def receive_json(self, content, **kwargs):
        type_ = content.get('type')
        if type_ == 'typing' and getattr(self, 'group_name', None):
            async_to_sync(self.channel_layer.group_send)(self.group_name, {
                'type': 'typing.event',
                'user_id': self.user.id,
                'nom': self.user.get_full_name() or self.user.username,
                'typing': bool(content.get('typing')),
            })

    # ------------------------------------------------------------------
    # Handlers d'evenements de groupe (le nom de methode = `type` avec les
    # points remplaces par des underscores, convention Channels).
    # ------------------------------------------------------------------
    def nouveau_message(self, event):
        self.send_json({'type': 'nouveau_message'})

    def message_modifie(self, event):
        self.send_json({'type': 'message_modifie'})

    def message_supprime(self, event):
        self.send_json({'type': 'message_supprime'})

    def typing_event(self, event):
        if event['user_id'] == self.user.id:
            return  # ne pas se renvoyer son propre "en train d'ecrire"
        self.send_json({
            'type': 'typing', 'user_id': event['user_id'],
            'nom': event['nom'], 'typing': event['typing'],
        })
