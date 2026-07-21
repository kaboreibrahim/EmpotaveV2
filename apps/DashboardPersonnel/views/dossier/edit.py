from django.urls import reverse_lazy
from django.views.generic import UpdateView

from apps.conteneurs.models import Dossier

from ..mixins import FormMessageMixin, ModulePermissionRequiredMixin
from .create import DossierForm, DossierOptionsMixin


class ModifierDossier(ModulePermissionRequiredMixin, DossierOptionsMixin, FormMessageMixin, UpdateView):
    model = Dossier
    form_class = DossierForm
    template_name = 'DashboardPersonnel/pages/dossier/create.html'
    success_url = reverse_lazy('DashboardPersonnel:dossier-liste')
    success_message = "Le dossier « %(TRD)s » a ete modifie avec succes."
