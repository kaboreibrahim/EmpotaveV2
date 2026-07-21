from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied


class ClientRequiredMixin(LoginRequiredMixin):
    """Restreint l'accès aux utilisateurs de type 'client' possédant un profil Client."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not hasattr(request.user, 'client'):
            raise PermissionDenied("Cet espace est réservé aux clients.")
        return super().dispatch(request, *args, **kwargs)
