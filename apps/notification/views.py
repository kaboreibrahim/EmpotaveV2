from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Notification


def _retour(request):
    return redirect(request.META.get('HTTP_REFERER') or '/')


@login_required
@require_POST
def marquer_lue(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=['is_read'])
    return _retour(request)


@login_required
@require_POST
def marquer_toutes_lues(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return _retour(request)
