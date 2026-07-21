"""
apps/audit/signals.py
Reçoit pre_save/post_save/post_delete pour TOUS les modèles (connectés sans
`sender` dans apps.py) et écrit une ligne AuditLog pour chaque création,
modification (avec diff champ par champ) ou suppression détectée sur un
modèle appartenant à une app du projet (apps.*).
"""
import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models import FileField

from .middleware import get_current_ip, get_current_user
from .models import AuditLog

logger = logging.getLogger(__name__)

SENSITIVE_FIELD_TOKENS = ('password', 'code', 'token', 'secret')


def _is_tracked(sender):
    app_config = getattr(sender._meta, 'app_config', None)
    if app_config is None:
        return False
    return app_config.name.startswith('apps.') and app_config.name != 'apps.audit'


def _serialize(instance):
    data = {}
    for field in instance._meta.concrete_fields:
        try:
            value = field.value_from_object(instance)
        except Exception:
            continue
        if isinstance(field, FileField):
            value = value.name if value else None
        data[field.name] = value
    return data


def _is_sensitive(field_name):
    return any(token in field_name.lower() for token in SENSITIVE_FIELD_TOKENS)


def _redact(key, value):
    return '***' if value and _is_sensitive(key) else value


def _diff(old_data, new_data):
    # Comparer sur les valeurs brutes : si on redacte avant de comparer, un
    # changement de mot de passe/code (old='***', new='***') devient invisible.
    changes = {}
    for key in set(old_data) | set(new_data):
        old_value = old_data.get(key)
        new_value = new_data.get(key)
        if old_value != new_value:
            changes[key] = {'old': _redact(key, old_value), 'new': _redact(key, new_value)}
    return changes


def pre_save_snapshot(sender, instance, raw=False, **kwargs):
    if raw or not _is_tracked(sender) or not instance.pk:
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    instance._audit_pre_save_data = _serialize(old_instance)


def log_save(sender, instance, created, raw=False, **kwargs):
    if raw or not _is_tracked(sender):
        return

    new_data = _serialize(instance)

    if created:
        changes = {key: {'old': None, 'new': _redact(key, value)} for key, value in new_data.items()}
        action = AuditLog.ACTION_CREATE
    else:
        old_data = getattr(instance, '_audit_pre_save_data', None) or {}
        changes = _diff(old_data, new_data)
        if not changes:
            return
        # safedelete fait un soft delete via save() (champ 'deleted' renseigné)
        # plutôt qu'un vrai DELETE SQL : on le relabellise pour rester lisible.
        soft_delete = changes.get('deleted')
        if soft_delete and soft_delete['old'] is None and soft_delete['new'] is not None:
            action = AuditLog.ACTION_DELETE
        else:
            action = AuditLog.ACTION_UPDATE

    _write_log(sender, instance, action, changes)


def log_delete(sender, instance, **kwargs):
    if not _is_tracked(sender):
        return
    old_data = _serialize(instance)
    changes = {key: {'old': _redact(key, value), 'new': None} for key, value in old_data.items()}
    _write_log(sender, instance, AuditLog.ACTION_DELETE, changes)


def _write_log(sender, instance, action, changes):
    user = get_current_user()
    if user is not None and not getattr(user, 'is_authenticated', False):
        user = None

    try:
        AuditLog.objects.create(
            action=action,
            content_type=ContentType.objects.get_for_model(sender),
            object_id=str(instance.pk),
            object_repr=str(instance)[:255],
            user=user,
            actor_username=user.get_username() if user else '',
            ip_address=get_current_ip(),
            changes=changes,
        )
    except Exception:
        logger.exception("Échec de l'écriture du journal d'audit pour %s", sender)
