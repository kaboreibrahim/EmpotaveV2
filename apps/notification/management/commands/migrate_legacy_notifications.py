"""
Migre les anciennes notifications (conteneurs_notification, liées au
Personnel via l'ancien schéma) vers apps.notification.Notification.

Prérequis : migrate_legacy_conteneurs doit avoir tourné avant (les ids
Users du personnel sont préservés depuis legacy_conteneurs_personnel).

Usage : python manage.py migrate_legacy_notifications [--dry-run]
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.users.models import Users
from apps.notification.models import Notification


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


class Command(BaseCommand):
    help = "Migre les anciennes notifications vers apps.notification.Notification."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        count = 0
        skipped = 0
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute("SELECT * FROM conteneurs_notification WHERE deleted IS NULL")
                rows = dictfetchall(cur)
            for row in rows:
                try:
                    user = Users.objects.get(id=row['user_id'])
                except Users.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"Notification #{row['id']} : utilisateur {row['user_id']} introuvable, ignorée."
                    ))
                    skipped += 1
                    continue
                _, created = Notification.objects.get_or_create(
                    user=user,
                    message=row['message'],
                    defaults={'is_read': row['is_read']},
                )
                if created:
                    count += 1
                else:
                    skipped += 1
            self.stdout.write(self.style.SUCCESS(f"OK — {count} notifications migrées, {skipped} ignorées."))
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry-run : rollback effectué."))
