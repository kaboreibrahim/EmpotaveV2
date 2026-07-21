import logging
import random
import re
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from ..models import CodeVerication

logger = logging.getLogger(__name__)

User = get_user_model()

CODE_RE = re.compile(r'^\d{4}$')
RESET_CODE_VALIDITY = timedelta(minutes=15)
MAX_VERIFY_ATTEMPTS = 5


def _generate_reset_code():
    return f'{random.randint(0, 999999):06d}'


def _find_user(identifiant):
    try:
        return User.objects.get(Q(username__iexact=identifiant) | Q(email__iexact=identifiant))
    except User.DoesNotExist:
        return None
    except User.MultipleObjectsReturned:
        return (
            User.objects.filter(Q(username__iexact=identifiant) | Q(email__iexact=identifiant))
            .order_by('pk')
            .first()
        )


def _get_reset_user(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return None
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


def _clear_reset_session(request):
    for key in ('reset_user_id', 'reset_code_verified', 'reset_attempts'):
        request.session.pop(key, None)


# ---------------------------------------------------------------
# Étape 1 : demande de réinitialisation (identifiant ou e-mail)
# ---------------------------------------------------------------
def forgot_password_view(request):
    if request.method == 'POST':
        identifiant = request.POST.get('email', '').strip()

        user = _find_user(identifiant)
        if user is None:
            messages.error(request, "Aucun compte n'est associé à cet identifiant.")
            return render(request, 'users/forgot.html')

        if not user.email:
            messages.error(request, "Aucune adresse e-mail n'est enregistrée pour ce compte.")
            return render(request, 'users/forgot.html')

        code = _generate_reset_code()
        user_name = user.get_full_name() or user.username
        validity_minutes = int(RESET_CODE_VALIDITY.total_seconds() // 60)

        try:
            html_content = render_to_string('emails/reset_code.html', {
                'user_name': user_name,
                'code': code,
                'validity_minutes': validity_minutes,
            })
            send_mail(
                'Votre code de réinitialisation',
                (
                    f"Bonjour {user_name},\n\n"
                    f"Votre code de réinitialisation à 6 chiffres est : {code}\n\n"
                    f"Ce code expire dans {validity_minutes} minutes."
                ),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=html_content,
            )
        except Exception:
            logger.exception("Échec de l'envoi du code de réinitialisation à %s", user.email)
            messages.error(request, "L'envoi de l'e-mail a échoué. Veuillez réessayer plus tard.")
            return render(request, 'users/forgot.html')

        CodeVerication.objects.update_or_create(
            user=user,
            defaults={'code': code, 'typecode': 'rest', 'date_created': timezone.now()},
        )

        request.session['reset_user_id'] = str(user.pk)
        request.session['reset_code_verified'] = False
        request.session['reset_attempts'] = 0

        logger.info('Code de réinitialisation envoyé à %s', user.email)
        return redirect('users:reset_verify')

    return render(request, 'users/forgot.html')


# ---------------------------------------------------------------
# Étape 2 : saisie du code à 6 chiffres reçu par e-mail
# ---------------------------------------------------------------
def verify_reset_code_view(request):
    user = _get_reset_user(request)
    if user is None:
        messages.error(request, "Veuillez recommencer la procédure de réinitialisation.")
        return redirect('users:forgot_password')

    if request.method == 'POST':
        submitted_code = request.POST.get('code', '').strip()

        try:
            verification = CodeVerication.objects.get(user=user, typecode='rest')
        except CodeVerication.DoesNotExist:
            messages.error(request, "Veuillez recommencer la procédure de réinitialisation.")
            _clear_reset_session(request)
            return redirect('users:forgot_password')

        if timezone.now() - verification.date_created > RESET_CODE_VALIDITY:
            messages.error(request, "Ce code a expiré. Veuillez en demander un nouveau.")
            _clear_reset_session(request)
            return redirect('users:forgot_password')

        if submitted_code and submitted_code == verification.code:
            request.session['reset_code_verified'] = True
            return redirect('users:reset_new_code')

        request.session['reset_attempts'] = request.session.get('reset_attempts', 0) + 1
        if request.session['reset_attempts'] >= MAX_VERIFY_ATTEMPTS:
            messages.error(request, "Trop de tentatives incorrectes. Veuillez recommencer la procédure.")
            _clear_reset_session(request)
            return redirect('users:forgot_password')

        messages.error(request, 'Code incorrect.')

    return render(request, 'users/reset_verify.html', {'email': user.email})


# ---------------------------------------------------------------
# Étape 3 : choix du nouveau code de connexion (4 chiffres)
# ---------------------------------------------------------------
def set_new_code_view(request):
    user = _get_reset_user(request)
    if user is None or not request.session.get('reset_code_verified'):
        messages.error(request, "Veuillez recommencer la procédure de réinitialisation.")
        _clear_reset_session(request)
        return redirect('users:forgot_password')

    if request.method == 'POST':
        new_code = request.POST.get('new_code', '')
        confirm_code = request.POST.get('confirm_code', '')

        if not CODE_RE.match(new_code):
            messages.error(request, 'Le code doit contenir exactement 4 chiffres.')
        elif new_code != confirm_code:
            messages.error(request, 'Les deux codes ne correspondent pas.')
        else:
            user.set_password(new_code)
            user.save(update_fields=['password'])
            CodeVerication.objects.filter(user=user, typecode='rest').delete()
            _clear_reset_session(request)

            messages.success(request, 'Votre code de connexion a été mis à jour. Vous pouvez vous connecter.')
            return redirect('users:login')

    return render(request, 'users/reset_new_code.html')
