"""
Tente de rattacher chaque compte Client (suivi empotage) sans lien encore a
une ClientEntreprise, par correspondance exacte de nom (voir
Client.resoudre_client_entreprise). A lancer apres sync_clients_stock, ou
periodiquement pour rattraper les nouveaux comptes clients crees entretemps.
Les correspondances non trouvees restent a corriger a la main dans l'admin
(le nom du compte de connexion ne correspond pas toujours au nom de la
societe cote oils-stock-api — voir la section 7 du dossier d'integration).

Usage : python manage.py link_clients_stock
"""
from django.core.management.base import BaseCommand

from apps.users.models import Client


class Command(BaseCommand):
    help = "Rattache les comptes Client non lies a leur ClientEntreprise par correspondance de nom."

    def handle(self, *args, **options):
        clients_non_lies = Client.objects.filter(client_entreprise__isnull=True).select_related('user')

        lies = 0
        non_trouves = []
        for client in clients_non_lies:
            if client.resoudre_client_entreprise():
                lies += 1
            else:
                non_trouves.append(str(client))

        self.stdout.write(self.style.SUCCESS(f"{lies} compte(s) client rattache(s)."))
        if non_trouves:
            self.stdout.write(f"{len(non_trouves)} compte(s) sans correspondance trouvee :")
            for nom in non_trouves:
                self.stdout.write(f"  - {nom}")
