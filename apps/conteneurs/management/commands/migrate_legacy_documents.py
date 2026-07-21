"""
Migre les anciens documents (FactureCommerciale, PackingList) de l'app
racine "conteneurs" (désinstallée) vers le nouveau modèle générique
apps.documents.Document.

Usage : python manage.py migrate_legacy_documents [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.conteneurs.models import Dossier
from apps.documents.models import TypeDocument, Document


STATUT_MAP = {
    'Terminé':    'valide',
    'En Attente': 'en_attente_validation',
}

LEGACY_TABLES = {
    'conteneurs_facturecommerciale':        'Facture Commerciale',
    'conteneurs_packinglist':               'Packing List',
    'conteneurs_certificatorigine':         "Certificat d'Origine",
    'conteneurs_confirmationbooking':       'Confirmation du Booking',
    'conteneurs_certificatphytosanitaire':  'Certificat Phytosanitaire',
    'conteneurs_copiesbls':                 'Copies des BLS',
    'conteneurs_rapportempotage':           "Rapport d'Empotage",
    'conteneurs_rapportselection':          'Rapport de Sélection',
    'conteneurs_autorisationexploitation':  "Autorisation d'exportation",
    'conteneurs_ec':                        'EC',
    'conteneurs_coa':                       'COA',
    'conteneurs_declaration':               'Declaration',
    'conteneurs_ier_entre':                 "IER D'ENTRE",
    'conteneurs_ier_sortie':                'IER DE SORTIE',
}


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


class Command(BaseCommand):
    help = "Migre les anciens documents (factures, packing lists) vers apps.documents."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        count = 0
        skipped = 0
        with transaction.atomic():
            for table, type_label in LEGACY_TABLES.items():
                type_doc, _ = TypeDocument.objects.get_or_create(type_document=type_label)
                with connection.cursor() as cur:
                    cur.execute(f"SELECT * FROM {table}")
                    rows = dictfetchall(cur)
                for row in rows:
                    try:
                        dossier = Dossier.objects.get(id=row['dossier_id'])
                    except Dossier.DoesNotExist:
                        self.stdout.write(self.style.WARNING(
                            f"{type_label} #{row['id']} : dossier {row['dossier_id']} introuvable, ignoré."
                        ))
                        skipped += 1
                        continue
                    _, created = Document.objects.get_or_create(
                        dossier=dossier,
                        type_document=type_doc,
                        fichier=row['fichier'],
                        defaults={'statut': STATUT_MAP.get(row['statut'], 'en_attente_validation')},
                    )
                    if created:
                        count += 1
                    else:
                        skipped += 1
            self.stdout.write(self.style.SUCCESS(f"OK — {count} documents migrés, {skipped} ignorés."))
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry-run : rollback effectué."))
