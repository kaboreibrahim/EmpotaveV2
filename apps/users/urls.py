from django.urls import path
from django.views.generic import RedirectView

from .views.forgot import forgot_password_view, set_new_code_view, verify_reset_code_view
from .views.login import login_view
from .views.logout import logout_view

app_name = 'users'

urlpatterns = [
    path('', RedirectView.as_view(url='/login/'), name='login'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('mot-de-passe-oublie/', forgot_password_view, name='forgot_password'),
    path('mot-de-passe-oublie/verifier/', verify_reset_code_view, name='reset_verify'),
    path('mot-de-passe-oublie/nouveau-code/', set_new_code_view, name='reset_new_code'),
]
