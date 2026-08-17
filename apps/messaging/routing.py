from django.urls import re_path

from . import consumers

_WS_PATH_PREFIX = '/ws/messaging/conversations/'


def ws_path(conversation_id, absolute=False, secure=False, host=None):
    """Chemin (ou URL absolue) du WebSocket d'une conversation. Une seule
    definition partagee avec `websocket_urlpatterns` ci-dessous, pour ne
    jamais desynchroniser le chemin construit cote vue (realtime.js) et
    celui reellement route par Channels."""
    path = f'{_WS_PATH_PREFIX}{conversation_id}/'
    if not absolute:
        return path
    scheme = 'wss' if secure else 'ws'
    return f'{scheme}://{host}{path}'


websocket_urlpatterns = [
    re_path(
        r'^' + _WS_PATH_PREFIX.lstrip('/') + r'(?P<conversation_id>[0-9a-fA-F-]+)/$',
        consumers.ConversationConsumer.as_asgi(),
    ),
]
