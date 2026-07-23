from django.db.models import Sum
from django.db.models.functions import ExtractMonth
from django.utils import timezone
from django.views.generic import TemplateView

from apps.conteneurs.models import Dossier
from apps.users.models import Client

from ..mixins import ComptableRequiredMixin

DASHBOARD_TEMPLATE = 'comptabiliteDashboard/dashboard.html'

# Même palette / noms de mois que le dashboard Personnel (apps/DashboardPersonnel/views/accueil.py)
PALETTE_GRAPHIQUES = ['#002046', '#505f76', '#87a0cd', '#f1bd81', '#321c00', '#ba1a1a', '#74777f']
COULEUR_PAYE = '#00450d'
COULEUR_EN_ATTENTE = '#964900'
NOMS_MOIS = [
    'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre',
]

# Même seuil que "dossiers bloqués" côté Personnel (apps/DashboardPersonnel/views/accueil.py)
JOURS_ALERTE_PAIEMENT = 14
NOMBRE_TOP_CLIENTS = 5


class DashboardComptableView(ComptableRequiredMixin, TemplateView):
    """Tableau de bord du service comptable : dossiers en attente/payés + statistiques simples."""

    template_name = DASHBOARD_TEMPLATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Dossier.objects.select_related('Id_Pays', 'id_client__user', 'utilisateur_paiement')

        total_dossiers = qs.count()
        total_en_attente = qs.filter(est_paye=False).count()
        total_payes = qs.filter(est_paye=True).count()

        context['total_dossiers'] = total_dossiers
        context['total_en_attente'] = total_en_attente
        context['total_payes'] = total_payes
        context['pct_payes'] = round(total_payes / total_dossiers * 100) if total_dossiers else 0

        repartition_statuts = [
            {'label': label, 'total': qs.filter(statut=valeur).count()}
            for valeur, label in Dossier.STATUT_CHOICES
        ]
        context['repartition_statuts'] = repartition_statuts
        statuts_non_vides = [ligne for ligne in repartition_statuts if ligne['total']]
        context['labels_statuts'] = [ligne['label'] for ligne in statuts_non_vides]
        context['valeurs_statuts'] = [ligne['total'] for ligne in statuts_non_vides]
        context['couleurs_statuts'] = (PALETTE_GRAPHIQUES * 2)[:len(statuts_non_vides)]

        context['labels_paiement'] = ['Payé', 'En attente de paiement']
        context['valeurs_paiement'] = [total_payes, total_en_attente]
        context['couleurs_paiement'] = [COULEUR_PAYE, COULEUR_EN_ATTENTE]

        context['dossiers_en_attente'] = (
            qs.filter(est_paye=False).order_by('-date_created')[:8]
        )
        context['dossiers_payes_recents'] = (
            qs.filter(est_paye=True).order_by('-date_paiement')[:8]
        )

        # --- Montants encaissés (basés sur les paiements validés) ------------
        maintenant = timezone.now()
        paiements = qs.filter(est_paye=True, montant_paiement__isnull=False)

        context['montant_total'] = paiements.aggregate(total=Sum('montant_paiement'))['total'] or 0
        context['montant_ce_mois'] = (
            paiements
            .filter(date_paiement__year=maintenant.year, date_paiement__month=maintenant.month)
            .aggregate(total=Sum('montant_paiement'))['total'] or 0
        )
        context['mois_courant_label'] = NOMS_MOIS[maintenant.month - 1]

        par_mois_qs = (
            paiements
            .filter(date_paiement__year=maintenant.year)
            .annotate(mois=ExtractMonth('date_paiement'))
            .values('mois')
            .annotate(total=Sum('montant_paiement'))
        )
        montant_par_mois = {ligne['mois']: float(ligne['total'] or 0) for ligne in par_mois_qs}
        context['labels_montants_mois'] = NOMS_MOIS
        context['valeurs_montants_mois'] = [montant_par_mois.get(mois, 0) for mois in range(1, 13)]
        context['annee_courante'] = maintenant.year

        # --- Comparaison vs mois précédent -----------------------------------
        mois_precedent = maintenant.month - 1 or 12
        annee_mois_precedent = maintenant.year if maintenant.month > 1 else maintenant.year - 1
        montant_mois_precedent = (
            paiements
            .filter(date_paiement__year=annee_mois_precedent, date_paiement__month=mois_precedent)
            .aggregate(total=Sum('montant_paiement'))['total'] or 0
        )
        context['montant_mois_precedent'] = montant_mois_precedent
        context['mois_precedent_label'] = NOMS_MOIS[mois_precedent - 1]
        if montant_mois_precedent:
            context['evolution_pct'] = round(
                (float(context['montant_ce_mois']) - float(montant_mois_precedent)) / float(montant_mois_precedent) * 100
            )
        elif context['montant_ce_mois']:
            context['evolution_pct'] = 100
        else:
            context['evolution_pct'] = 0

        # --- Délai moyen de paiement (création -> validation), en jours -----
        delais = [
            (paiement.date_paiement.date() - paiement.date_created.date()).days
            for paiement in qs.filter(est_paye=True, date_paiement__isnull=False)
        ]
        context['delai_moyen_paiement'] = round(sum(delais) / len(delais), 1) if delais else None

        # --- Top clients par montant encaissé ---------------------------------
        top_clients_agg = (
            paiements
            .values('id_client')
            .annotate(total=Sum('montant_paiement'))
            .order_by('-total')[:NOMBRE_TOP_CLIENTS]
        )
        clients_par_id = {
            client.pk: client
            for client in Client.objects.select_related('user').filter(
                pk__in=[ligne['id_client'] for ligne in top_clients_agg]
            )
        }
        context['top_clients'] = [
            {'client': clients_par_id.get(ligne['id_client']), 'total': ligne['total']}
            for ligne in top_clients_agg
        ]

        # --- Alertes : dossiers en attente de paiement depuis longtemps -------
        seuil_alerte = maintenant - timezone.timedelta(days=JOURS_ALERTE_PAIEMENT)
        context['jours_alerte_paiement'] = JOURS_ALERTE_PAIEMENT
        context['dossiers_alerte_paiement'] = (
            qs.filter(est_paye=False, date_created__lt=seuil_alerte).order_by('date_created')
        )

        return context
