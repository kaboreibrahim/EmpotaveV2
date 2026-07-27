import json

from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.finders import find as find_static
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Notification, PushSubscription


def _retour(request):
    return redirect(request.META.get('HTTP_REFERER') or '/')


@login_required
@require_POST
def marquer_lue(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=['is_read'])
    if notif.url:
        return redirect(notif.url)
    return _retour(request)


@login_required
@require_POST
def marquer_toutes_lues(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return _retour(request)


@login_required
@require_POST
def push_subscribe(request):
    """Enregistre (ou met à jour) l'abonnement Push envoyé par le navigateur
    de l'utilisateur connecté (voir static/notification/js/push-notifications.js).
    Ce n'est pas une API REST : un simple endpoint POST classique, appelé en
    JavaScript depuis les pages du site, comme le reste de l'application.
    """
    try:
        payload = json.loads(request.body)
        endpoint = payload['endpoint']
        p256dh = payload['keys']['p256dh']
        auth = payload['keys']['auth']
    except (KeyError, ValueError, TypeError):
        return HttpResponseBadRequest("Abonnement Push invalide.")

    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            'utilisateur': request.user,
            'p256dh': p256dh,
            'auth': auth,
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255],
        },
    )
    return JsonResponse({'success': True})


@login_required
@require_POST
def push_unsubscribe(request):
    """Supprime l'abonnement Push dont l'endpoint est fourni (désactivation
    volontaire des notifications par l'utilisateur)."""
    try:
        endpoint = json.loads(request.body)['endpoint']
    except (KeyError, ValueError, TypeError):
        return HttpResponseBadRequest("Requête invalide.")

    PushSubscription.objects.filter(endpoint=endpoint, utilisateur=request.user).delete()
    return JsonResponse({'success': True})


def service_worker(request):
    """Sert le Service Worker depuis la racine du site (`/sw.js`), condition
    nécessaire pour qu'il puisse contrôler toutes les pages du domaine (une
    portée `/static/...` limiterait les notifications aux seules pages sous
    ce préfixe). Le fichier reste rangé avec les autres statiques de l'app."""
    chemin = find_static('notification/js/service-worker.js')
    with open(chemin, 'rb') as fichier:
        response = HttpResponse(fichier.read(), content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response
