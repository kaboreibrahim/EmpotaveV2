"""
apps/comptabiliteDashboard/mixins.py
Contrôle d'accès : réservé au groupe Django "Comptable" (+ superuser).
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

GROUPE_COMPTABLE = 'Comptable'


def est_comptable(user):
    return user.is_superuser or user.groups.filter(name=GROUPE_COMPTABLE).exists()


class ComptableRequiredMixin(LoginRequiredMixin):
    """Réserve l'accès aux membres du groupe "Comptable" (ou aux superusers)."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not est_comptable(request.user):
            raise PermissionDenied("Cet espace est réservé au service comptable.")
        return super().dispatch(request, *args, **kwargs)
