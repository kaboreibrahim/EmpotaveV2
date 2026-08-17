"""
Cree la conversation "dossier" (et ses membres) pour tous les Dossiers deja
existants avant l'introduction de la messagerie : le signal post_save sur
Dossier (voir apps.messaging.signals) ne s'applique qu'aux sauvegardes
futures, ce backfill couvre l'historique.

Usage : python manage.py backfill_dossier_conversations
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.conteneurs.models import Dossier
from apps.messaging.signals import synchroniser_conversation_dossier


class Command(BaseCommand):
    help = "Cree retroactivement la conversation principale des dossiers existants."

    @transaction.atomic
    def handle(self, *args, **options):
        dossiers = Dossier.objects.all()
        total = dossiers.count()
        crees = 0
        for dossier in dossiers.iterator():
            from apps.messaging.models import Conversation
            existait = Conversation.objects.filter(
                dossier=dossier, type_conversation=Conversation.TYPE_DOSSIER,
            ).exists()
            synchroniser_conversation_dossier(Dossier, dossier, created=False)
            if not existait:
                crees += 1
        self.stdout.write(self.style.SUCCESS(
            f"{crees} conversation(s) creee(s) sur {total} dossier(s) traite(s)."
        ))
