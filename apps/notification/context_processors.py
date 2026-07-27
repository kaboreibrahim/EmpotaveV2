"""
apps/notification/context_processors.py
Rend les notifications de l'utilisateur connecté disponibles dans tous les
templates (cloche de notification des barres de navigation), ainsi que la
clé publique VAPID nécessaire à l'abonnement Web Push côté navigateur.
"""
from django.conf import settings


def notifications(request):
    context = {'VAPID_PUBLIC_KEY': settings.VAPID_PUBLIC_KEY}
    if not request.user.is_authenticated:
        return context
    qs = request.user.notifications.order_by('-date_created')
    context.update({
        'notifications_recentes': qs[:8],
        'notifications_non_lues': qs.filter(is_read=False).count(),
        'alertes_non_lues': qs.filter(is_read=False, categorie='alerte'),
    })
    return context
