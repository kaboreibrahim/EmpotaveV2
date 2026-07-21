"""
apps/audit/services.py
Point d'entrée pour journaliser manuellement une action qui n'est pas détectée
par les signaux post_save/post_delete (ex: téléchargement ou soumission d'un
rapport, qui ne modifient pas forcément l'objet en base).
"""
from django.contrib.contenttypes.models import ContentType

from .middleware import get_current_ip, get_current_user
from .models import AuditLog


def log_action(instance, action, extra=None):
    """Écrit une ligne AuditLog pour `action` sur `instance`, avec l'utilisateur
    et l'IP de la requête en cours (voir middleware.CurrentRequestMiddleware)."""
    user = get_current_user()
    if user is not None and not getattr(user, 'is_authenticated', False):
        user = None

    AuditLog.objects.create(
        action=action,
        content_type=ContentType.objects.get_for_model(instance),
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        user=user,
        actor_username=user.get_username() if user else '',
        ip_address=get_current_ip(),
        changes=extra or {},
    )
