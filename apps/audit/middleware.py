"""
apps/audit/middleware.py
Expose l'utilisateur et l'IP de la requête en cours aux signaux du modèle
(signals.py), qui n'ont pas accès à la requête HTTP.
"""
import threading

_state = threading.local()


def get_current_user():
    return getattr(_state, 'user', None)


def get_current_ip():
    return getattr(_state, 'ip', None)


class CurrentRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _state.user = getattr(request, 'user', None)
        _state.ip = self._client_ip(request)
        try:
            return self.get_response(request)
        finally:
            _state.user = None
            _state.ip = None

    @staticmethod
    def _client_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
