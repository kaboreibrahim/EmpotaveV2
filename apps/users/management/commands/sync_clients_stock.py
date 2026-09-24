"""
Synchronise le referentiel ClientEntreprise depuis les clients d'oils-stock-api
(GET /api/v1/clients/) : upsert par stock_client_id si deja lie, sinon par
code. Ne touche jamais les societes creees localement sans code ni
stock_client_id (rien ne les relie a un client distant a matcher).

Usage : python manage.py sync_clients_stock
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.conteneurs.stock_client import StockServiceIndisponible, lister_clients
from apps.users.models import ClientEntreprise


class Command(BaseCommand):
    help = "Importe/actualise les societes clientes depuis oils-stock-api."

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            clients_distants = lister_clients()
        except StockServiceIndisponible as exc:
            raise CommandError(f"oils-stock-api injoignable : {exc}") from exc

        crees = maj = 0
        for client in clients_distants:
            stock_client_id = client["id"]
            code = client.get("code") or None
            defaults = {
                "nom": client["nom"],
                "code": code,
                "actif": client.get("actif", True),
            }

            objet = ClientEntreprise.objects.filter(stock_client_id=stock_client_id).first()
            if objet is None and code:
                # Societe deja creee localement (sans lien stock) sous le meme
                # code : on la relie au lieu d'en creer une deuxieme.
                objet = ClientEntreprise.objects.filter(code=code, stock_client_id__isnull=True).first()

            if objet is not None:
                for champ, valeur in {**defaults, "stock_client_id": stock_client_id}.items():
                    setattr(objet, champ, valeur)
                objet.save()
                maj += 1
            else:
                ClientEntreprise.objects.create(stock_client_id=stock_client_id, **defaults)
                crees += 1

        self.stdout.write(self.style.SUCCESS(
            f"{crees} societe(s) creee(s), {maj} mise(s) a jour sur {len(clients_distants)} client(s) recu(s)."
        ))
