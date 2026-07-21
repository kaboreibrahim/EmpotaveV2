from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


def logout_view(request):
    if request.method == 'POST':
        prenom = ''
        if request.user.is_authenticated:
            prenom = request.user.get_full_name() or request.user.username
        logout(request)
        if prenom:
            messages.success(request, f"À bientôt {prenom} ! Vous avez été déconnecté.")
        return redirect('users:login')
    return redirect('users:login')
