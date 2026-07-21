from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth
from django.shortcuts import render
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.conteneurs.models import Dossier, Flexitanks, ISOTanks
from apps.documents.models import Document, TypeDocument
from apps.users.models import Agent_empotage, Agent_selection, Client

STATUTS_ACTIFS = ('en_attente', 'selection_en_cours', 'empotage_en_cours')
STATUTS_EN_COURS = ('selection_en_cours', 'empotage_en_cours')
JOURS_DOSSIER_BLOQUE = 14
NOMBRE_CLIENTS_AFFICHES = 6

NOMS_MOIS = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]

# Palette réutilisée pour les graphiques (mêmes tons que le reste du design system).
PALETTE_GRAPHIQUES = ['#002046', '#505f76', '#87a0cd', '#f1bd81', '#321c00', '#ba1a1a', '#74777f']


def _nom_client(ligne):
    prenom = ligne.get('id_client__user__first_name') or ''
    nom = ligne.get('id_client__user__last_name') or ''
    nom_complet = f"{prenom} {nom}".strip()
    return nom_complet or ligne.get('id_client__user__username') or 'Client inconnu'


@login_required
def DashboardPersonnel(request):
    """Tableau de bord du Personnel : vue transversale sur tous les dossiers,
    agents et documents (contrairement aux dashboards agents, restreints à
    leurs propres dossiers)."""
    maintenant = timezone.now()

    dossiers = Dossier.objects.select_related(
        'Id_Pays', 'Id_Agent_selection__user', 'Id_Agent_empotage__user', 'id_client__user',
    )
    dossiers_actifs = dossiers.filter(statut__in=STATUTS_ACTIFS)

    # --- KPIs ---------------------------------------------------------------
    total_dossiers_actifs = dossiers_actifs.count()
    total_en_attente = dossiers.filter(statut='en_attente').count()
    total_en_cours = dossiers.filter(statut__in=STATUTS_EN_COURS).count()
    total_termines_mois = dossiers.filter(
        statut='dossier_termine',
        date_created__year=maintenant.year,
        date_created__month=maintenant.month,
    ).count()

    nb_iso = ISOTanks.objects.count()
    nb_flexi = Flexitanks.objects.count()
    total_conteneurs = nb_iso + nb_flexi

    total_types_requis = TypeDocument.objects.count()
    total_documents_attendus = total_types_requis * total_dossiers_actifs
    total_documents_ajoutes = Document.objects.filter(dossier__in=dossiers_actifs).count()
    taux_completion_documentaire = (
        round(total_documents_ajoutes / total_documents_attendus * 100) if total_documents_attendus else 0
    )

    # --- Dossiers récents, avec progression documentaire ---------------------
    dossiers_recents = dossiers.annotate(
        nb_documents=Count('documents', distinct=True)
    ).order_by('-date_created')[:8]

    # --- Répartition par statut ----------------------------------------------
    repartition_statut = [
        {'valeur': valeur, 'label': label, 'nombre': dossiers.filter(statut=valeur).count()}
        for valeur, label in Dossier.STATUT_CHOICES
    ]

    # --- Alertes ---------------------------------------------------------------
    dossiers_documents_rejetes = (
        dossiers_actifs.filter(documents__statut='rejete').distinct()[:5]
    )
    dossiers_sans_agent = dossiers_actifs.filter(
        Q(statut__in=('en_attente', 'selection_en_cours'), Id_Agent_selection__isnull=True)
        | Q(statut='empotage_en_cours', Id_Agent_empotage__isnull=True)
    ).distinct()[:5]
    seuil_blocage = maintenant - timezone.timedelta(days=JOURS_DOSSIER_BLOQUE)
    dossiers_bloques = dossiers_actifs.filter(
        statut__in=STATUTS_EN_COURS, date_created__lt=seuil_blocage
    ).order_by('date_created')[:5]

    # --- Activité récente (journal d'audit, toutes apps confondues) ----------
    activite_recente = AuditLog.objects.select_related('user').order_by('-created_at')[:8]

    # --- Charge de travail par agent ------------------------------------------
    charge_agents_selection = list(
        Agent_selection.objects.select_related('user').annotate(
            nb_dossiers=Count('dossiers', filter=Q(dossiers__statut__in=STATUTS_ACTIFS))
        ).filter(nb_dossiers__gt=0).order_by('-nb_dossiers')[:5]
    )
    charge_agents_empotage = list(
        Agent_empotage.objects.select_related('user').annotate(
            nb_dossiers=Count('dossiers', filter=Q(dossiers__statut__in=STATUTS_ACTIFS))
        ).filter(nb_dossiers__gt=0).order_by('-nb_dossiers')[:5]
    )

    # --- Répartition des dossiers par client ----------------------------------
    dossiers_avec_client = dossiers.exclude(id_client__isnull=True)
    total_dossiers_avec_client = dossiers_avec_client.count()
    par_client_qs = (
        dossiers_avec_client
        .values('id_client__user__first_name', 'id_client__user__last_name', 'id_client__user__username')
        .annotate(nb=Count('id'))
        .order_by('-nb')
    )
    top_clients = list(par_client_qs[:NOMBRE_CLIENTS_AFFICHES])
    labels_clients = [_nom_client(ligne) for ligne in top_clients]
    valeurs_clients = [ligne['nb'] for ligne in top_clients]
    reste_clients = total_dossiers_avec_client - sum(valeurs_clients)
    if reste_clients > 0:
        labels_clients.append('Autres clients')
        valeurs_clients.append(reste_clients)
    client_principal = labels_clients[0] if labels_clients else None
    client_principal_nb = valeurs_clients[0] if valeurs_clients else 0

    # --- Répartition des dossiers par commodité -------------------------------
    par_commodite_qs = (
        dossiers
        .values('Id_Commodite__nom')
        .annotate(nb=Count('id'))
        .order_by('-nb')
    )
    labels_commodites = [ligne['Id_Commodite__nom'] for ligne in par_commodite_qs]
    valeurs_commodites = [ligne['nb'] for ligne in par_commodite_qs]

    # --- Répartition des dossiers par mois (toutes années confondues) --------
    par_mois_qs = (
        dossiers
        .annotate(mois=ExtractMonth('date_created'))
        .values('mois')
        .annotate(nb=Count('id'))
    )
    compte_par_mois = {ligne['mois']: ligne['nb'] for ligne in par_mois_qs}
    labels_mois = NOMS_MOIS
    valeurs_mois = [compte_par_mois.get(mois, 0) for mois in range(1, 13)]
    mois_pic_index = valeurs_mois.index(max(valeurs_mois)) if any(valeurs_mois) else None
    mois_pic = NOMS_MOIS[mois_pic_index] if mois_pic_index is not None else None

    # --- Statistiques des conteneurs par client (filtrable par année) --------
    annees_disponibles = sorted(
        {d.year for d in Dossier.objects.dates('date_created', 'year')}, reverse=True
    )
    annee_param = request.GET.get('annee', '').strip()
    if annee_param.isdigit() and int(annee_param) in annees_disponibles:
        annee_selectionnee = int(annee_param)
    elif annees_disponibles:
        annee_selectionnee = annees_disponibles[0]
    else:
        annee_selectionnee = maintenant.year

    lignes_brutes = (
        dossiers.filter(date_created__year=annee_selectionnee, id_client__isnull=False)
        .values('id_client', 'type_conteneur')
        .annotate(nb_iso=Count('isotanks', distinct=True), nb_flexi=Count('flexitanks', distinct=True))
    )
    par_client = {}
    for ligne in lignes_brutes:
        compteurs = par_client.setdefault(ligne['id_client'], {})
        compteurs[ligne['type_conteneur']] = ligne['nb_iso'] + ligne['nb_flexi']

    stats_conteneurs_par_client = []
    total_general_conteneurs = 0
    total_general_iso = 0
    for client in Client.objects.select_related('user', 'user__pays'):
        valeurs = par_client.get(client.pk, {})
        p10 = valeurs.get('10_pieds', 0)
        p20 = valeurs.get('20_pieds', 0)
        p40 = valeurs.get('40_pieds', 0)
        iso = valeurs.get('ISO_20_pieds', 0)
        total_conteneurs_client = p10 + p20 + p40
        total_general_client = total_conteneurs_client + iso
        stats_conteneurs_par_client.append({
            'client': client, 'p10': p10, 'p20': p20, 'p40': p40, 'iso': iso,
            'total_conteneurs': total_conteneurs_client, 'total_iso': iso,
            'total_general': total_general_client,
        })
        total_general_conteneurs += total_conteneurs_client
        total_general_iso += iso
    stats_conteneurs_par_client.sort(key=lambda l: (-l['total_general'], str(l['client'])))

    # --- Conteneurs utilisés par mois (chronologique, année sélectionnée) ----
    mois_max = maintenant.month if annee_selectionnee == maintenant.year else 12
    iso_par_mois_chrono = {
        ligne['mois']: ligne['nb'] for ligne in (
            ISOTanks.objects.filter(date_created__year=annee_selectionnee)
            .annotate(mois=ExtractMonth('date_created')).values('mois').annotate(nb=Count('id'))
        )
    }
    flexi_par_mois_chrono = {
        ligne['mois']: ligne['nb'] for ligne in (
            Flexitanks.objects.filter(date_created__year=annee_selectionnee)
            .annotate(mois=ExtractMonth('date_created')).values('mois').annotate(nb=Count('id'))
        )
    }
    labels_mois_chrono = [f"{annee_selectionnee}-{mois:02d}" for mois in range(1, mois_max + 1)]
    labels_mois_chrono_complet = [f"{NOMS_MOIS[mois - 1].lower()} {annee_selectionnee}" for mois in range(1, mois_max + 1)]
    valeurs_conteneurs_mois_chrono = [
        iso_par_mois_chrono.get(mois, 0) + flexi_par_mois_chrono.get(mois, 0)
        for mois in range(1, mois_max + 1)
    ]

    return render(request, 'DashboardPersonnel/pages/accueil.html', {
        'total_dossiers_actifs': total_dossiers_actifs,
        'total_en_attente': total_en_attente,
        'total_en_cours': total_en_cours,
        'total_termines_mois': total_termines_mois,
        'nb_iso': nb_iso,
        'nb_flexi': nb_flexi,
        'total_conteneurs': total_conteneurs,
        'pct_iso': round(nb_iso / total_conteneurs * 100) if total_conteneurs else 0,
        'pct_flexi': round(nb_flexi / total_conteneurs * 100) if total_conteneurs else 0,
        'taux_completion_documentaire': taux_completion_documentaire,
        'total_types_requis': total_types_requis,
        'dossiers_recents': dossiers_recents,
        'repartition_statut': repartition_statut,
        'dossiers_documents_rejetes': dossiers_documents_rejetes,
        'dossiers_sans_agent': dossiers_sans_agent,
        'dossiers_bloques': dossiers_bloques,
        'activite_recente': activite_recente,
        'charge_agents_selection': charge_agents_selection,
        'charge_agents_empotage': charge_agents_empotage,
        'jours_dossier_bloque': JOURS_DOSSIER_BLOQUE,
        'labels_clients': labels_clients,
        'valeurs_clients': valeurs_clients,
        'couleurs_clients': (PALETTE_GRAPHIQUES * 2)[:len(labels_clients)],
        'client_principal': client_principal,
        'client_principal_nb': client_principal_nb,
        'total_dossiers_avec_client': total_dossiers_avec_client,
        'labels_mois': labels_mois,
        'valeurs_mois': valeurs_mois,
        'mois_pic': mois_pic,
        'labels_commodites': labels_commodites,
        'valeurs_commodites': valeurs_commodites,
        'couleurs_commodites': (PALETTE_GRAPHIQUES * 2)[:len(labels_commodites)],
        'stats_conteneurs_par_client': stats_conteneurs_par_client,
        'annees_disponibles': annees_disponibles,
        'annee_selectionnee': annee_selectionnee,
        'total_general_conteneurs': total_general_conteneurs,
        'total_general_iso': total_general_iso,
        'total_general_grand': total_general_conteneurs + total_general_iso,
        'labels_mois_chrono': labels_mois_chrono,
        'labels_mois_chrono_complet': labels_mois_chrono_complet,
        'valeurs_conteneurs_mois_chrono': valeurs_conteneurs_mois_chrono,
    })
