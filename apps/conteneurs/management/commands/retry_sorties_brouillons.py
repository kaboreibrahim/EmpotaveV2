"""
Retente la creation du brouillon de sortie oils-stock-api pour les Dossiers
qui en sont restes prives (panne reseau a la creation, ou societe cliente
resolue/liee apres coup) — voir option a du dossier d'integration EmpotaveV2.
La societe cliente est deduite depuis le Client (compte de suivi empotage) du
dossier, voir Client.resoudre_client_entreprise().

Usage : python manage.py retry_sorties_brouillons
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.conteneurs.models import Dossier
from apps.conteneurs.stock_client import StockServiceIndisponible, creer_sortie_brouillon


class Command(BaseCommand):
    help = "Retente la creation du brouillon de sortie stock pour les dossiers qui en sont prives."

    def handle(self, *args, **options):
        dossiers = (
            Dossier.objects
            .filter(sortie_stock_id__isnull=True)
            .exclude(statut='annulé')
            .select_related('id_client__client_entreprise')
        )

        reussis = echecs = sans_lien = 0
        for dossier in dossiers.iterator():
            client_entreprise = dossier.id_client.resoudre_client_entreprise()
            if not client_entreprise or not client_entreprise.stock_client_id:
                sans_lien += 1
                continue
            try:
                sortie = creer_sortie_brouillon(
                    client_id=client_entreprise.stock_client_id,
                    projet=dossier.projet,
                    trd=dossier.TRD,
                    date_sortie=timezone.now().date(),
                )
            except StockServiceIndisponible as exc:
                echecs += 1
                self.stderr.write(f"Dossier {dossier.TRD} : {exc}")
                continue
            dossier.Id_ClientEntreprise = client_entreprise
            dossier.sortie_stock_id = sortie['id']
            dossier.sortie_stock_reference = sortie['reference']
            dossier.save(update_fields=['Id_ClientEntreprise', 'sortie_stock_id', 'sortie_stock_reference'])
            reussis += 1

        self.stdout.write(self.style.SUCCESS(
            f"{reussis} brouillon(s) cree(s), {echecs} echec(s), {sans_lien} dossier(s) sans societe cliente resolue."
        ))
