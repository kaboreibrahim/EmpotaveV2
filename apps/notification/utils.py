"""
apps/notification/utils.py
Envoi bas niveau des notifications Web Push (pywebpush + VAPID).

Ce module ne contient aucune logique métier : il sait seulement envoyer un
payload à un abonnement donné et nettoyer les abonnements expirés/invalides.
Toute la logique métier (qui notifier, quel message) reste dans services.py.
"""
import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

logger = logging.getLogger(__name__)


def get_vapid_claims():
    return {'sub': f"mailto:{settings.VAPID_ADMIN_EMAIL}"}


def send_web_push(subscription, payload):
    """Envoie `payload` (dict) à un `PushSubscription`.

    Ne lève jamais d'exception : toute erreur est journalisée. L'abonnement
    est supprimé automatiquement pour ne plus être retenté si le fournisseur
    (navigateur) répond qu'il n'existe plus (410 Gone / 404 Not Found), ou
    qu'il a été créé avec une autre paire de clés VAPID que celle configurée
    actuellement (403 après une rotation de clés côté serveur — ce cas précis
    est définitif, contrairement à un 403 pour une autre raison de config).
    """
    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {
                    'p256dh': subscription.p256dh,
                    'auth': subscription.auth,
                },
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=get_vapid_claims(),
        )
        return True
    except WebPushException as exc:
        status_code = getattr(exc.response, 'status_code', None)
        corps_reponse = getattr(exc.response, 'text', '') or ''
        cle_perimee = status_code == 403 and 'do not correspond' in corps_reponse
        if status_code in (404, 410) or cle_perimee:
            logger.info("Abonnement Push expiré/invalide, suppression : %s", subscription.endpoint)
            subscription.delete()
        else:
            logger.warning("Échec d'envoi Web Push (%s) : %s", status_code, exc)
        return False
    except Exception:
        logger.exception("Erreur inattendue lors de l'envoi Web Push vers %s", subscription.endpoint)
        return False
