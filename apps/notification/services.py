"""
apps/notification/services.py
Point d'entrée unique pour créer des notifications depuis les autres apps.
"""
from apps.users.models import Users

from .models import Notification


def notifier(users, message, categorie=Notification.CATEGORIE_INFO):
    """Crée une notification `message` pour chaque utilisateur de `users`.

    Accepte un seul utilisateur ou un itérable ; les valeurs vides (None) sont
    ignorées pour ne pas planter quand un champ FK optionnel (ex: Id_Personnel)
    n'est pas renseigné sur le dossier. `categorie` = 'alerte' fait apparaître
    un bandeau flottant rouge en haut du dashboard tant que la notification
    n'est pas lue (voir base_agent_empotage.html).
    """
    if hasattr(users, 'pk'):
        users = [users]
    Notification.objects.bulk_create([
        Notification(user=user, message=message, categorie=categorie) for user in users if user
    ])


def notifier_personnel(message):
    """Notifie tous les utilisateurs de type 'personnel' (pas seulement celui
    éventuellement assigné à un dossier via Id_Personnel)."""
    notifier(Users.objects.filter(user_type='personnel', is_active=True), message)
