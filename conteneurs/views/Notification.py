from conteneurs.models import Notification 
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def senf_notification(user,message):
    Notification.objects.create(user=user,message=message)
    
    
@login_required
def notification_view(request):
    
    notifiactions=request.user.notifications.filter(is_read=False)
    return render (request,'notification/notification_non_lue.html',{'notifiactions':notifiactions})