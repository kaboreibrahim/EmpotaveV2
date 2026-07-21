"""
apps/DashboardPersonnel/views/users.py
Vues CRUD (ListView / CreateView / UpdateView / DeleteView)
pour la gestion des Utilisateurs (Users).
"""
from django import forms
from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.users.models import Users

from .mixins import DeleteMessageMixin, FormMessageMixin, ModulePermissionRequiredMixin

# =============================================================================
# PERMISSIONS PAR MODULE
# =============================================================================

# (app_label, model, libelle affiche, icone material-symbols)
PERMISSION_MODELS = [
    ('referentiels', 'pays', 'Pays', 'public'),
    ('referentiels', 'commodite', 'Commodite', 'category'),
    ('referentiels', 'pol', 'POL', 'anchor'),
    ('referentiels', 'pod', 'POD', 'anchor'),
    ('referentiels', 'compagniemaritime', 'Compagnie maritime', 'directions_boat'),
    ('referentiels', 'siteselection', 'Site de selection', 'storefront'),
    ('referentiels', 'siteempotage', "Site d'empotage", 'warehouse'),
    ('conteneurs', 'dossier', 'Dossiers', 'folder'),
    ('documents', 'document', 'Documents', 'description'),
    ('users', 'users', 'Utilisateurs', 'group'),
]

ACTION_LABELS = {
    'view': 'Voir',
    'add': 'Ajouter',
    'change': 'Modifier',
    'delete': 'Supprimer',
}


def get_permission_queryset():
    query = Q()
    for app_label, model, *_rest in PERMISSION_MODELS:
        query |= Q(content_type__app_label=app_label, content_type__model=model)
    return Permission.objects.filter(query).select_related('content_type')


# =============================================================================
# FORMULAIRES
# =============================================================================

class UserForm(forms.ModelForm):
    """Informations du profil + code d'acces (4 chiffres) + permissions par module."""
    code = forms.CharField(
        label="Code d'acces (4 chiffres)",
        widget=forms.PasswordInput(attrs={'inputmode': 'numeric', 'maxlength': 4, 'autocomplete': 'new-password'}),
    )
    code_confirm = forms.CharField(
        label="Confirmer le code",
        widget=forms.PasswordInput(attrs={'inputmode': 'numeric', 'maxlength': 4, 'autocomplete': 'new-password'}),
    )
    user_permissions = forms.ModelMultipleChoiceField(
        queryset=get_permission_queryset(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Permissions',
    )

    class Meta:
        model = Users
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'numero', 'photo', 'user_type', 'pays', 'is_active',
            'user_permissions',
        ]

    def clean(self):
        cleaned_data = super().clean()
        code = cleaned_data.get('code')
        code_confirm = cleaned_data.get('code_confirm')
        if code or code_confirm:
            if code != code_confirm:
                self.add_error('code_confirm', 'Les deux codes ne correspondent pas.')
            else:
                try:
                    validate_password(code, self.instance)
                except forms.ValidationError as exc:
                    self.add_error('code', exc)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        code = self.cleaned_data.get('code')
        if code:
            user.set_password(code)
        if commit:
            user.save()
            self.save_m2m()
        return user

    def permission_groups(self):
        """Regroupe les cases a cocher de permissions par module, pour un affichage en matrice."""
        permissions = list(self.fields['user_permissions'].queryset)
        subwidgets = list(self['user_permissions'])
        action_order = list(ACTION_LABELS.values())

        groups = []
        for app_label, model, label, icon in PERMISSION_MODELS:
            rows = []
            for permission, subwidget in zip(permissions, subwidgets):
                if permission.content_type.app_label != app_label or permission.content_type.model != model:
                    continue
                action = permission.codename.split('_', 1)[0]
                rows.append({'action_label': ACTION_LABELS.get(action, action), 'subwidget': subwidget})
            rows.sort(key=lambda r: action_order.index(r['action_label']) if r['action_label'] in action_order else len(action_order))
            groups.append({'label': label, 'icon': icon, 'rows': rows})
        return groups


class UserUpdateForm(UserForm):
    """Le code d'acces devient optionnel : laisser vide conserve le code actuel."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].required = False
        self.fields['code'].label = 'Nouveau code (optionnel)'
        self.fields['code'].help_text = "Laisser vide pour conserver le code d'acces actuel."
        self.fields['code_confirm'].required = False
        self.fields['code_confirm'].label = 'Confirmer le nouveau code'


# =============================================================================
# LISTE
# =============================================================================

class UserListView(ModulePermissionRequiredMixin, ListView):
    """
    Liste paginée des utilisateurs avec recherche + filtres
    (type d'utilisateur, statut actif/inactif/en attente).
    """
    model = Users
    template_name = 'DashboardPersonnel/pages/utilisateur/liste.html'
    context_object_name = 'users'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('pays').order_by('-date_created')

        search = self.request.GET.get('q', '').strip()
        user_type = self.request.GET.get('user_type', '')
        status = self.request.GET.get('status', '')

        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(numero__icontains=search)
            )

        if user_type:
            queryset = queryset.filter(user_type=user_type)

        if status == 'active':
            queryset = queryset.filter(is_active=True, is_verified=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status == 'pending':
            queryset = queryset.filter(is_verified=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_type_choices'] = Users.USER_TYPE_CHOICES
        context['current_q'] = self.request.GET.get('q', '')
        context['current_user_type'] = self.request.GET.get('user_type', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['total_users'] = Users.objects.count()
        context['verified_users'] = Users.objects.filter(is_verified=True).count()
        context['pending_users'] = Users.objects.filter(is_verified=False).count()
        return context


# =============================================================================
# CRÉATION
# =============================================================================

class UserCreateView(ModulePermissionRequiredMixin, FormMessageMixin, CreateView):
    model = Users
    form_class = UserForm
    template_name = 'DashboardPersonnel/pages/utilisateur/create.html'
    success_url = reverse_lazy('DashboardPersonnel:user-list')
    success_message = "L'utilisateur « %(username)s » a ete cree avec succes."


# =============================================================================
# MODIFICATION
# =============================================================================

class UserUpdateView(ModulePermissionRequiredMixin, FormMessageMixin, UpdateView):
    model = Users
    form_class = UserUpdateForm
    template_name = 'DashboardPersonnel/pages/utilisateur/create.html'
    success_url = reverse_lazy('DashboardPersonnel:user-list')
    success_message = "L'utilisateur « %(username)s » a ete modifie avec succes."


# =============================================================================
# SUPPRESSION (soft-delete via SafeDeleteModel)
# =============================================================================

class UserDeleteView(ModulePermissionRequiredMixin, DeleteMessageMixin, DeleteView):
    model = Users
    template_name = 'DashboardPersonnel/pages/utilisateur/confirm_delete.html'
    context_object_name = 'user_obj'
    success_url = reverse_lazy('DashboardPersonnel:user-list')
    success_message = "L'utilisateur « %(object)s » a ete supprime avec succes."
