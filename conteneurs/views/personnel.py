from django.http import HttpRequest, HttpResponseRedirect
from django.views.generic import ListView, CreateView,UpdateView,DeleteView
from conteneurs.models import Personnel
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from braces.views import FormMessagesMixin
from django.db.models import Q

@method_decorator(login_required, name='dispatch')
class PersonnelView(ListView):
    model = Personnel
    context_object_name = 'Personnel_list'
    template_name = 'pages/Personnel/Personnel_list.html'
    paginate_by = 10  # Définit le nombre d'éléments par page

    def get_queryset(self):
        queryset = Personnel.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(Q(Contact__icontains=search) | Q(Date_ajout__icontains=search)|Q(username__icontains=search)|Q(email__icontains=search))
        return queryset.order_by('-Date_ajout')
             