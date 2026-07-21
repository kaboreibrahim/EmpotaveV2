from django.shortcuts import render, redirect
from django.contrib.auth import login,logout,authenticate,get_backends,get_user_model
from conteneurs.forms import *
from django.shortcuts import redirect
from conteneurs.models import VerificationCode
from django.contrib.auth.decorators import login_required
# view de creation de compte 
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import views as auth_views
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
#from taxi.models import P 
from django.core.exceptions import MultipleObjectsReturned
class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(Q(username=username) | Q(email=username))
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None        
    
       
def register(request):
    
    USER_TYPE_CHOICES = [
    ('Votre_fonction', 'Selectionne votre fonction'),

    ('agent_selection', 'Agent selection' ),
    ('agent_acconage', 'Agent  habillage et empotage'),
    ('secretaire', 'Secrétaire'),
    ('chef', 'Chef'),
]
    if request.method == 'POST':
        form = PersonnelForm(request.POST , request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('verify')  # Rediriger vers la page de vérification
    else:
        form = PersonnelForm()
    return render(request, 'registration/register.html', {'form': form, 'USER_TYPE_CHOICES': USER_TYPE_CHOICES})

# view de verification de creation de compte 

def verify(request):
    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                verification_code = VerificationCode.objects.get(code=code)
                user = verification_code.user
                user.is_active = True
                user.is_verified = True
                user.save()
                verification_code.delete()  # Supprimer le code de vérification après validation
                
                # Obtenir le backend d'authentification utilisé
                backend = get_backends()[0]
                login(request, user, backend='accounts.auth_backends.EmailOrUsernameModelBackend')
                return redirect('login')
            except VerificationCode.DoesNotExist:
                form.add_error('code', 'Code invalide')
    else:
        form = VerificationForm()
    return render(request, 'registration/verify.html', {'form': form})

"""
# view de connexion """
def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            try:
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('index')
                else:
                    form.add_error(None, 'Nom d\'utilisateur ou mot de passe incorrect')
            except MultipleObjectsReturned:
                form.add_error(None, 'Erreur : Plusieurs utilisateurs correspondent à ces informations.')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})


@login_required
def deconnection(request):
    logout(request)
    # Redirige l'utilisateur vers une page après la déconnexion (par exemple la page d'accueil)
    messages.add_message(request, messages.SUCCESS, " A bientot  " )

    return redirect('login')

#view reste password


class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'registration/rest/password_reset.html'

    def form_valid(self, form):
        email = form.cleaned_data.get('email')
        if not Personnel.objects.filter(email=email).exists():
            messages.error(self.request, "Cet email n'est associé à aucun compte utilisateur.")
            return self.form_invalid(form)
        return super().form_valid(form)


"""def password_reset_request_view(request):
    if request.method == "POST":
        email = request.POST['email']
        try:
            user =Personnel.objects.get(email=email)
            reset_code = PasswordResetCode.objects.create(user=user)
            send_mail(
                'Votre code de réinitialisation de mot de passe',
                f'Votre code de réinitialisation est : {reset_code.code} il expire dans 10 munites',
                'kaboremessi@gmail.com',
                [email],
                fail_silently=False,
            )
            messages.add_message(request, messages.SUCCESS,f' code verification envoye sur : {email} ' )
            return redirect('password_reset_verify')
        except User.DoesNotExist:
            # Gérer le cas où l'utilisateur n'existe pas
            messages.add_message(request, messages.WARNING, " L'email saisir est attribué a aucun utlisateur veilleur a bien verifier le mail " )

            pass
    return render(request, 'registration/password_reset.html')
"""

# view pour verifier le code a 6 chiffre 

"""
def password_reset_verify_view(request):
    if request.method == "POST":
        code = request.POST['code']
        try:
            reset_code = PasswordResetCode.objects.get(code=code)
            if reset_code.is_valid():
                request.session['reset_user_id'] = reset_code.user.id
                return redirect('password_reset_confirm')
            else:
                # Code expiré ou invalide
                messages.add_message(request, messages.WARNING, " Code expiré ou invalide " )
        except PasswordResetCode.DoesNotExist:
            # Code incorrect
            messages.add_message(request, messages.WARNING, " Code incorrect " )

            pass
    return render(request, 'registration/password_reset_verify.html')
"""
# view pour mettre a jour le nouveau de passe 


#User = get_user_model()

"""def password_reset_confirm_view(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('password_reset')

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('password_reset')

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, user)  # Optionnel : pour maintenir la session si l'utilisateur est connecté
            messages.add_message(request, messages.SUCCESS, "Votre mot de passe a été réinitialisé avec succès.")
            request.session.pop('reset_user_id', None)  # Nettoyer la session
            return redirect('login')
    else:
        form = SetPasswordForm(user)
    
    return render(request, 'registration/password_reset_confirm.html', {'form': form})
"""