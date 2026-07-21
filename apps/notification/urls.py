from django.urls import path

from . import views

app_name = 'notification'

urlpatterns = [
    path('<uuid:pk>/lue/', views.marquer_lue, name='marquer-lue'),
    path('toutes-lues/', views.marquer_toutes_lues, name='marquer-toutes-lues'),
]
