"""
config/asgi.py
Route HTTP vers l'application Django classique, WebSocket vers Channels
(voir apps.messaging.routing). `get_asgi_application()` doit être appelé
avant tout import qui touche le registre des apps Django (routing/consumers
compris) — sinon "Apps aren't loaded yet".
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

import apps.messaging.routing  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(apps.messaging.routing.websocket_urlpatterns)
        )
    ),
})
