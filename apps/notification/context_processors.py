"""
apps/notification/context_processors.py
Rend les notifications de l'utilisateur connecté disponibles dans tous les
templates (cloche de notification des barres de navigation), ainsi que la
clé publique VAPID nécessaire à l'abonnement Web Push côté navigateur.
"""
from django.conf import settings


def notifications(request):
    context = {'VAPID_PUBLIC_KEY': settings.VAPID_PUBLIC_KEY}
    # `request.user` n'existe pas encore si une exception a interrompu la
    # requête avant AuthenticationMiddleware (ex. Host non autorisé) : sans
    # ce garde-fou, le rendu de la page d'erreur elle-même plante en cascade.
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return context
    qs = request.user.notifications.order_by('-date_created')
    context.update({
        'notifications_recentes': qs[:8],
        'notifications_non_lues': qs.filter(is_read=False).count(),
        'alertes_non_lues': qs.filter(is_read=False, categorie='alerte'),
    })
    return context
