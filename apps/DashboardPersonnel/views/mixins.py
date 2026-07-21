from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView


class AjaxCreateMixin:
    """
    Permet a un CreateView de repondre en JSON ({id, label} ou {errors})
    quand la requete vient d'un quick-add (fetch avec X-Requested-With),
    pour l'ajout de donnees de reference sans quitter le formulaire appelant.
    """
    def _is_ajax(self):
        return self.request.headers.get('x-requested-with') == 'XMLHttpRequest'

    def form_valid(self, form):
        response = super().form_valid(form)
        if self._is_ajax():
            return JsonResponse({'id': str(self.object.pk), 'label': str(self.object)})
        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)
        if self._is_ajax():
            return JsonResponse({'errors': form.errors}, status=400)
        return response


class FormMessageMixin(SuccessMessageMixin):
    """Message de succes (Create/Update) et message d'erreur si le formulaire est invalide."""
    error_message = "Veuillez corriger les erreurs du formulaire."

    def form_invalid(self, form):
        messages.error(self.request, self.error_message)
        return super().form_invalid(form)


class DeleteMessageMixin:
    """Message de succes apres suppression, construit a partir de l'objet supprime."""
    success_message = "%(object)s a ete supprime avec succes."

    def form_valid(self, form):
        message = self.success_message % {'object': str(self.object)}
        response = super().form_valid(form)
        messages.success(self.request, message)
        return response


class ModulePermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Verifie que l'utilisateur possede la permission Django correspondant
    au modele et au type de vue CRUD (view/add/change/delete), deduite
    automatiquement de `self.model` et de la classe de vue heritee.

    Utilisateur non connecte -> redirection vers la page de connexion.
    Utilisateur connecte sans la permission -> page 403 (Acces refuse).
    """

    def get_permission_required(self):
        if isinstance(self, (ListView, DetailView)):
            action = 'view'
        elif isinstance(self, CreateView):
            action = 'add'
        elif isinstance(self, UpdateView):
            action = 'change'
        elif isinstance(self, DeleteView):
            action = 'delete'
        else:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} doit heriter de ListView, DetailView, "
                "CreateView, UpdateView ou DeleteView pour utiliser ModulePermissionRequiredMixin."
            )
        opts = self.model._meta
        return (f'{opts.app_label}.{action}_{opts.model_name}',)


class ActionPermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Variante pour les vues qui ne sont pas des CRUD generiques (ex. actions
    Ajax sur une `View` simple) : la permission est fournie explicitement
    via l'attribut `permission_action` ('view'/'add'/'change'/'delete') et
    le modele cible via `permission_model`.
    """
    permission_model = None
    permission_action = None

    def get_permission_required(self):
        if self.permission_model is None or self.permission_action is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} doit definir 'permission_model' et "
                "'permission_action' pour utiliser ActionPermissionRequiredMixin."
            )
        opts = self.permission_model._meta
        return (f'{opts.app_label}.{self.permission_action}_{opts.model_name}',)
