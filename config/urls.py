"""
config/urls.py
Adapté depuis gestion_conteneurs/urls.py.
- Conserve i18n_patterns (langue FR/EN)
- Routage par app (users, conteneurs, documents, notifications)
- Statiques et médias en dev
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('admin/', admin.site.urls),
    path('referentiels/', include('apps.referentiels.urls')),
    path('',        include('apps.users.urls')),
    path('conteneurs/',   include('apps.conteneurs.urls')),
    path('documents/',    include('apps.documents.urls')),
    path('DashboardPersonnel/', include('apps.DashboardPersonnel.urls')),
    path('DashboardClient/', include('apps.DashboardClient.urls')),
    path('DashboardAgentSelection/', include('apps.DashboardAgentSelection.urls')),
    path('DashboardAgentEmpotage/', include('apps.DashboardAgentEmpotage.urls')),
    path('notifications/', include('apps.notification.urls')),
]




urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)


# ---------------------------------------------------------------
# Pages d'erreur personnalisées (actives uniquement quand DEBUG=False)
# ---------------------------------------------------------------
handler400 = 'apps.error.views.bad_request'
handler403 = 'apps.error.views.permission_denied'
handler404 = 'apps.error.views.page_not_found'
handler500 = 'apps.error.views.server_error'
