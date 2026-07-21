from django.shortcuts import render
from django.contrib import messages
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.views import View
from conteneurs.models import *  # Assurez-vous que le modèle Dossier est correctement importé
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from datetime import timedelta
from django.views.generic import TemplateView
from django.utils.timezone import now

def index(request):
    # Message de bienvenue avec le nom d'utilisateur
    messages.add_message(request, messages.SUCCESS, f"Bienvenue {request.user.username}")

    # Filtrer les utilisateurs en ligne
    users_online = Personnel.objects.filter(is_online=True)

    # Nombre d'utilisateurs en ligne
    num_connected_users = users_online.count()

    # Filtrer les dossiers pour l'utilisateur william avec le client spécifique
    if request.user.username == "william":
        dossiers_client = Dossier.objects.filter(client__nom="REUSE TRADING NV")
    else:
        dossiers_client = Dossier.objects.all()

    # Nombre de dossiers en attente et autres statistiques
    selection_en_cours = dossiers_client.filter(statut="selection_en_cours").count()

    conteneurs_par_mois = Conteneur.objects.annotate(
        month=TruncMonth('Date_ajout')
    ).values('month').annotate(total=Count('id')).order_by('month')

    current_month = now().month
    current_year = now().year
    dossiers_termine_mois = dossiers_client.filter(statut="dossier_termine", Date_ajout__month=current_month, Date_ajout__year=current_year).count()

    dossiers_attente_mois = dossiers_client.filter(statut="en_attente", Date_ajout__month=current_month, Date_ajout__year=current_year).count()

    dossiers_termine_annee = dossiers_client.filter(statut="dossier_termine", Date_ajout__year=current_year).count()

    conteneurs_annee = Conteneur.objects.filter(Date_ajout__year=current_year).count()

    current_date = now()
    dossiers_mois = dossiers_client.filter(Date_ajout__month=current_month, Date_ajout__year=current_year).count()

    dossiers_aconage_mois = dossiers_client.filter(statut="aconage_en_cours", Date_ajout__month=current_month, Date_ajout__year=current_year).count()

    # Préparer les données pour Morris.js
    data = [{'month': item['month'].strftime('%Y-%m'), 'count': item['total']} for item in conteneurs_par_mois]

    Nbre_conteneur = Conteneur.objects.filter(Date_ajout__year=current_year).count()

    # Passer les informations au template
    context = {
        'num_connected_users': num_connected_users,
        'selection_en_cours': selection_en_cours,
        'conteneur_data': data,
        'conteneurs_annee': conteneurs_annee,
        'dossiers_termine_annee': dossiers_termine_annee,
        'dossiers_termine_mois': dossiers_termine_mois,
        'current_date': current_date,
        'dossiers_mois': dossiers_mois,
        'dossiers_attente_mois': dossiers_attente_mois,
        'dossiers_aconage_mois': dossiers_aconage_mois,
        'Nbre_conteneur': Nbre_conteneur,
    }

    return render(request, "index.html", context)

class DossierStatsDataView(View):
    def get(self, request, *args, **kwargs):
        # Vérifier si l'utilisateur est william
        if request.user.username == "william":
            # Filtrer les dossiers uniquement pour le client "REUSE TRADING NV"
            dossiers = Dossier.objects.filter(client__nom="REUSE TRADING NV")
        else:
            # Sinon, récupérer tous les dossiers
            dossiers = Dossier.objects.all()

        # Obtenir les statistiques des 12 derniers mois
        current_date = timezone.now()
        start_date = current_date - timedelta(days=365)
        
        # Requête pour tous les dossiers par mois
        total_dossiers = (
            dossiers
            .filter(date_creation__gte=start_date)
            .annotate(month=TruncMonth('date_creation'))
            .values('month')
            .annotate(total_dossiers=Count('id'))
            .order_by('month')
        )
        
        # Requête pour les dossiers terminés par mois
        dossiers_termines = (
            dossiers
            .filter(
                date_creation__gte=start_date,
                statut='dossier_termine'
            )
            .annotate(month=TruncMonth('date_creation'))
            .values('month')
            .annotate(dossiers_termines=Count('id'))
            .order_by('month')
        )
        
        # Créer un dictionnaire pour combiner les résultats
        stats_by_month = {}
        
        # Ajouter les totaux
        for entry in total_dossiers:
            month_str = entry['month'].strftime('%B %Y')
            stats_by_month[month_str] = {
                'month': month_str,
                'total_dossiers': entry['total_dossiers'],
                'dossiers_termines': 0
            }
        
        # Ajouter les dossiers terminés
        for entry in dossiers_termines:
            month_str = entry['month'].strftime('%B %Y')
            if month_str in stats_by_month:
                stats_by_month[month_str]['dossiers_termines'] = entry['dossiers_termines']
        
        # Convertir en liste pour l'API
        stats_list = list(stats_by_month.values())
        
        return JsonResponse(stats_list, safe=False)


from django.http import JsonResponse
from django.db.models import Count

def get_commodity_stats(request):
    # Vérifiez si l'utilisateur est connecté et récupérez l'utilisateur
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'error': 'Utilisateur non authentifié'}, status=401)

    # Obtenez les statistiques d'utilisation des commodités
    commodity_stats = Dossier.objects.values(
        'commodite__nom_commodite'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Si l'utilisateur est 'william', filtrez les dossiers du client 'REUSE TRADING NV'
    if user.username == 'william':
        commodity_stats = commodity_stats.filter(client__nom='REUSE TRADING NV')
    
    # Formatez les données pour Morris.js
    data = [{
        'commodity': item['commodite__nom_commodite'],
        'count': item['count']
    } for item in commodity_stats]
    
    return JsonResponse(data, safe=False)


from django.db.models import Count, Q
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
@method_decorator(login_required, name='dispatch')
class ClientConteneursStatsView(View):
    template_name = 'client_conteneurs_stats.html'
    
    def get(self, request, *args, **kwargs):
        # Récupérer l'année sélectionnée (par défaut : année en cours)
        selected_year = int(request.GET.get('year', timezone.now().year))
        
        # Récupérer toutes les années disponibles
        years = Dossier.objects.dates('date_creation', 'year').values_list('date_creation__year', flat=True).distinct()
        if not years:
            years = [timezone.now().year]
        
        # Récupérer tous les clients actifs
        clients = Client.objects.all().order_by('nom')
        
        # Préparer les données pour chaque client
        clients_data = []
        for client in clients:
            # Filtrer les dossiers par année
            dossiers = client.dossier_set.filter(date_creation__year=selected_year)
            
            # Initialiser les compteurs
            details = {
                '10_pieds': 0,
                '20_pieds': 0,
                'ISO_20_pieds': 0,
                '40_pieds': 0
            }
            
            # Compter les conteneurs par type pour l'année sélectionnée
            for dossier in dossiers:
                if dossier.type_conteneur in details:
                    details[dossier.type_conteneur] += dossier.conteneurs.count()
            
            # Calculer les totaux
            total_iso_tanks = details['ISO_20_pieds']
            total_conteneurs = sum(details[t] for t in ['10_pieds', '20_pieds', '40_pieds'])
            
            clients_data.append({
                'client': client,
                'total_conteneurs': total_conteneurs,
                'total_iso_tanks': total_iso_tanks,
                'details': details
            })
        
        # Trier les clients par nombre total de conteneurs (du plus grand au plus petit)
        clients_data.sort(key=lambda x: x['total_conteneurs'] + x['total_iso_tanks'], reverse=True)
        
        # Calculer les totaux généraux
        total_general_conteneurs = sum(item['total_conteneurs'] for item in clients_data)
        total_general_iso_tanks = sum(item['total_iso_tanks'] for item in clients_data)
        
        context = {
            'clients_data': clients_data,
            'total_general_conteneurs': total_general_conteneurs,
            'total_general_iso_tanks': total_general_iso_tanks,
            'total_general': total_general_conteneurs + total_general_iso_tanks,
            'years': sorted(years, reverse=True),
            'selected_year': selected_year
        }
        
        return render(request, self.template_name, context)