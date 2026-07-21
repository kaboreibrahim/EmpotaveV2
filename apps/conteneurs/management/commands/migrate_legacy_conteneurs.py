"""
Migre les données de l'ancien schéma (tables legacy_conteneurs_* / conteneurs_*
issues de l'app racine "conteneurs", désormais désinstallée) vers le nouveau
schéma (apps.referentiels, apps.users, apps.conteneurs).

Usage : python manage.py migrate_legacy_conteneurs [--dry-run]
"""
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.referentiels.models import (
    Pays, Commodite, POL, POD, CompagnieMaritime, SiteSelection, SiteEmpotage,
)
from apps.users.models import Users, Personnel, Client, Agent_selection, Agent_empotage
from apps.conteneurs.models import Dossier, ISOTanks, Flexitanks


STATUT_DOSSIER_MAP = {
    'en_attente': 'en_attente',
    'selection_en_cours': 'selection_en_cours',
    'Aconage_en_cours': 'empotage_en_cours',
    'ACCONAGE_FAIT': 'dossier_termine',
    'dossier_termine': 'dossier_termine',
}

PERSONNEL_TYPE_TO_USER_TYPE = {
    'agent_selection': 'agent_selection',
    'agent_acconage': 'agent_empotage',
    'secretaire': 'personnel',
    'chef': 'personnel',
}


def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


class Command(BaseCommand):
    help = "Migre les anciennes données conteneurs vers le nouveau schéma."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        with transaction.atomic():
            self.personnel_map = {}  # old personnel id (int) -> (user_type, wrapper_instance)
            self._migrate_referentiels()
            self._migrate_personnel()
            self._reset_users_sequence()
            self._migrate_clients()
            dossier_count = self._migrate_dossiers()
            conteneur_count = self._migrate_conteneurs()
            self.stdout.write(self.style.SUCCESS(
                f"OK — {dossier_count} dossiers, {conteneur_count} conteneurs migrés."
            ))
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry-run : rollback effectué, rien n'a été écrit."))

    # ------------------------------------------------------------------
    def _fetch(self, sql):
        with connection.cursor() as cur:
            cur.execute(sql)
            return dictfetchall(cur)

    # ------------------------------------------------------------------
    def _migrate_referentiels(self):
        for row in self._fetch("SELECT * FROM conteneurs_pays WHERE deleted IS NULL"):
            Pays.objects.update_or_create(id=row['id'], defaults={'nom': row['nom']})

        for row in self._fetch("SELECT * FROM conteneurs_commodite WHERE deleted IS NULL"):
            Commodite.objects.update_or_create(id=row['id'], defaults={
                'nom': row['nom_commodite'], 'Id_Pays_id': row['pays_id'],
            })

        for row in self._fetch("SELECT * FROM conteneurs_pol WHERE deleted IS NULL"):
            POL.objects.update_or_create(id=row['id'], defaults={
                'nom': row['nom_POL'], 'lieu': row['lieu_POL'], 'Id_Pays_id': row['pays_id'],
            })

        for row in self._fetch("SELECT * FROM conteneurs_pod WHERE deleted IS NULL"):
            POD.objects.update_or_create(id=row['id'], defaults={
                'nom': row['nom_POD'], 'lieu': row['lieu_POD'], 'Id_Pays_id': row['pays_id'],
            })

        for row in self._fetch("SELECT * FROM conteneurs_compagniemaritime WHERE deleted IS NULL"):
            CompagnieMaritime.objects.update_or_create(id=row['id'], defaults={
                'nom': row['nom_compagnie_maritime'], 'lieu': row['lieu_compagnie_maritime'],
                'Id_Pays_id': row['pays_id'],
            })

        for row in self._fetch("SELECT * FROM conteneurs_site WHERE deleted IS NULL"):
            SiteSelection.objects.update_or_create(id=row['id'], defaults={
                'nom': row['nom_site'], 'contact': row['contact_site'], 'lieu': row['lieu_site'],
                'Id_Pays_id': row['pays_id'],
            })

        for row in self._fetch("SELECT * FROM conteneurs_site_empotage WHERE deleted IS NULL"):
            SiteEmpotage.objects.update_or_create(id=row['id'], defaults={
                'nom': row['nom_site'], 'contact': row['contact_site'], 'lieu': row['lieu_site'],
                'Id_Pays_id': row['pays_id'],
            })

    # ------------------------------------------------------------------
    def _migrate_personnel(self):
        rows = self._fetch("SELECT * FROM legacy_conteneurs_personnel WHERE deleted IS NULL")
        for row in rows:
            user_type = PERSONNEL_TYPE_TO_USER_TYPE.get(row['Personnel_type'], 'personnel')
            user, _ = Users.objects.update_or_create(
                id=row['id'],
                defaults={
                    'username': row['username'],
                    'email': row['email'] or '',
                    'first_name': row['first_name'] or '',
                    'last_name': row['last_name'] or '',
                    'password': row['password'],
                    'is_staff': row['is_staff'],
                    'is_active': row['is_active'],
                    'is_superuser': row['is_superuser'],
                    'last_login': row['last_login'],
                    'date_joined': row['Date_ajout'],
                    'numero': row['Contact'],
                    'photo': row['photos'],
                    'is_verified': row['is_verified'],
                    'is_online': row['is_online'],
                    'user_type': user_type,
                },
            )
            if user_type == 'agent_selection':
                wrapper, _ = Agent_selection.objects.update_or_create(user=user)
            elif user_type == 'agent_empotage':
                wrapper, _ = Agent_empotage.objects.update_or_create(user=user)
            else:
                wrapper, _ = Personnel.objects.update_or_create(user=user)
            self.personnel_map[row['id']] = (user_type, wrapper)

    # ------------------------------------------------------------------
    def _reset_users_sequence(self):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT setval(pg_get_serial_sequence('users_users', 'id'), "
                "COALESCE((SELECT MAX(id) FROM users_users), 1))"
            )

    # ------------------------------------------------------------------
    def _migrate_clients(self):
        self.client_map = {}
        used_usernames = set(Users.objects.values_list('username', flat=True))
        for row in self._fetch("SELECT * FROM conteneurs_client WHERE deleted IS NULL"):
            username = row['email'] or f"client-{row['id']}"
            base_username = username
            n = 1
            while username in used_usernames:
                n += 1
                username = f"{base_username}-{n}"
            used_usernames.add(username)

            user = Users.objects.create(
                username=username,
                email=row['email'] or '',
                first_name=row['nom'] or '',
                password=make_password(None),
                user_type='client',
                date_joined=row['Date_ajout'],
                numero=row['contact'],
                pays_id=row['pays_id'],
            )
            client, _ = Client.objects.update_or_create(id=row['id'], defaults={'user': user})
            self.client_map[row['id']] = client

    # ------------------------------------------------------------------
    def _migrate_dossiers(self):
        self.dossier_map = {}
        rows = self._fetch("SELECT * FROM legacy_conteneurs_dossier WHERE deleted IS NULL")
        for row in rows:
            agent_selection = None
            agent_empotage = None
            personel = None

            if row['agent_selection_id'] is not None:
                utype, wrapper = self.personnel_map.get(row['agent_selection_id'], (None, None))
                if utype == 'agent_selection':
                    agent_selection = wrapper

            if row['agent_acconage_id'] is not None:
                utype, wrapper = self.personnel_map.get(row['agent_acconage_id'], (None, None))
                if utype == 'agent_empotage':
                    agent_empotage = wrapper

            if row['secretaire_id'] is not None:
                utype, wrapper = self.personnel_map.get(row['secretaire_id'], (None, None))
                if utype == 'personnel':
                    personel = wrapper

            client = self.client_map.get(row['client_id'])
            if client is None:
                self.stdout.write(self.style.WARNING(
                    f"Dossier {row['TRD']} : client {row['client_id']} introuvable, ignoré."
                ))
                continue

            dossier = Dossier.objects.create(
                id=row['id'],
                statut=STATUT_DOSSIER_MAP.get(row['statut'], 'en_attente'),
                TRD=row['TRD'],
                projet=row['projet'],
                Booking=row['booking'],
                type_conteneur=row['type_conteneur'],
                date_de_selection=row['Date_selection'],
                date_de_empotage=row['Date_acconage'],
                Id_Pays_id=row['pays_id'],
                Id_POD_id=row['port_de_dechargement_id'],
                Id_POL_id=row['port_de_chargement_id'],
                Id_Commodite_id=row['commodite_id'],
                Id_CompagnieMaritime_id=row['compagnie_maritime_id'],
                Id_SiteSelection_id=row['site_id'],
                Id_SiteEmpotage_id=row['Site_empotage_id'],
                Id_Agent_selection=agent_selection,
                Id_Agent_empotage=agent_empotage,
                id_client=client,
                Id_Personnel=personel,
            )
            self.dossier_map[row['id']] = dossier
        return len(self.dossier_map)

    # ------------------------------------------------------------------
    def _migrate_conteneurs(self):
        count = 0
        rows = self._fetch("SELECT * FROM conteneurs_conteneur WHERE deleted IS NULL")
        for row in rows:
            dossier = self.dossier_map.get(row['dossier_id'])
            if dossier is None:
                self.stdout.write(self.style.WARNING(
                    f"Conteneur {row['reference']} : dossier {row['dossier_id']} introuvable, ignoré."
                ))
                continue

            champs_communs = dict(
                id=row['id'],
                dossier=dossier,
                statut='empote' if row['statut'] == 'aconer' else 'non_empote',
                reference=row['reference'],
                etat=row['etat'],
                photo_devant=row['photo_devant'],
                photo_derriere=row['photo_derriere'],
                photo_interieur=row['photo_interieur'],
                photo_lateral_droit=row['photo_lateral_droit'],
                photo_lateral_gauche=row['photo_lateral_gauche'],
                Temerature=row['temperature'],
                poids_net=row['poids_net'],
            )

            if dossier.type_conteneur == 'ISO_20_pieds':
                ISOTanks.objects.create(
                    **champs_communs,
                    plombAmateur1=row['numero_plomb'],
                    photoPlombAmateur1=row['photo_plomb'],
                    plombAmateur2=row['numero_plomb2'],
                    photoPlombAmateur2=row['photo_plomb2'],
                    plombAmateur3=row['numero_plomb3'],
                    photoPlombAmateur3=row['photo_plomb3'],
                    Plombs_oils1=row['numero_plomb4'],
                    photo_plombs_oils1=row['photo_plomb4'],
                    Plombs_oils2=row['numero_plomb5'],
                    photo_plombs_oils2=row['photo_plomb5'],
                )
            else:
                Flexitanks.objects.create(
                    **champs_communs,
                    poids_brute=row['poids_brute'],
                    poids_equipements=row['poids_equipements'],
                    Numeroheatingpad=row['numero_heating_pad'],
                    Photoheatingpad=row['photo_heating_pad'],
                    numeroFlextank=row['numero_flexitank'],
                    photoFlextank=row['photo_flexitank'],
                    plombs_amateur=row['numero_plomb'],
                    plombs_amateur_photo=row['photo_plomb'],
                    Plombs_oils=row['numero_plomb2'],
                    photo_plombs_oils=row['photo_plomb2'],
                )
            count += 1
        return count
