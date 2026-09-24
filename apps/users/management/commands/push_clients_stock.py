"""
Migre vers oils-stock-api les comptes Client (suivi empotage) qui n'ont pas
encore de societe liee : cree la societe cote oils-stock-api (POST
/api/v1/clients/) puis la ClientEntreprise locale correspondante, et la lie
au compte. Inverse de sync_clients_stock (qui importe depuis oils-stock-api).

Les comptes dont le nom affiche ressemble a une adresse e-mail (pas un vrai
nom de societe, ex. compte cree avec l'e-mail comme identifiant et sans
prenom/nom) sont exclus et listes a part : les creer tel quel cote
oils-stock-api produirait une "societe" nommee comme une adresse e-mail.
Corriger le nom du compte (ou le lier a la main) avant de relancer.

Usage : python manage.py push_clients_stock
"""
import re

from django.core.management.base import BaseCommand

from apps.conteneurs.stock_client import StockServiceIndisponible, creer_client_stock
from apps.users.models import Client, ClientEntreprise

RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _generer_code(nom):
    base = re.sub(r"[^A-Z0-9]", "", nom.upper())[:16]
    return base or "CLIENT"


class Command(BaseCommand):
    help = "Cree cote oils-stock-api une societe pour chaque compte Client sans societe liee."

    def handle(self, *args, **options):
        clients_sans_lien = Client.objects.filter(client_entreprise__isnull=True).select_related("user")

        migres = echecs = 0
        exclus = []
        for client in clients_sans_lien:
            nom = (client.user.get_full_name() or client.user.username).strip()
            if not nom:
                continue
            if RE_EMAIL.match(nom):
                exclus.append(nom)
                continue

            code = _generer_code(nom)
            try:
                cree = creer_client_stock(nom=nom, code=code)
            except StockServiceIndisponible as exc:
                echecs += 1
                self.stderr.write(f"{nom} : {exc}")
                continue

            entreprise = ClientEntreprise.objects.create(
                nom=cree["nom"], code=cree.get("code") or None, stock_client_id=cree["id"],
            )
            client.client_entreprise = entreprise
            client.save(update_fields=["client_entreprise"])
            migres += 1

        self.stdout.write(self.style.SUCCESS(f"{migres} compte(s) migre(s), {echecs} echec(s)."))
        if exclus:
            self.stdout.write(
                f"{len(exclus)} compte(s) exclu(s) (nom affiche = adresse e-mail, "
                "a corriger avant migration) :"
            )
            for nom in exclus:
                self.stdout.write(f"  - {nom}")
