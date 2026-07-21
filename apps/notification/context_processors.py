"""
apps/notification/context_processors.py
Rend les notifications de l'utilisateur connecté disponibles dans tous les
templates (cloche de notification des barres de navigation).
"""


def notifications(request):
    if not request.user.is_authenticated:
        return {}
    qs = request.user.notifications.order_by('-date_created')
    return {
        'notifications_recentes': qs[:8],
        'notifications_non_lues': qs.filter(is_read=False).count(),
        'alertes_non_lues': qs.filter(is_read=False, categorie='alerte'),
    }
