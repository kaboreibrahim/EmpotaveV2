"""Crée le groupe Django "Comptable" et lui attribue les permissions nécessaires
pour valider les paiements et consulter les dossiers."""
from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations


def creer_groupe_comptable(apps, schema_editor):
    # Les permissions `can_valider_paiement`/`view_dossier` ne sont créées par Django
    # (signal post_migrate) qu'une fois toutes les migrations terminées : on les
    # génère donc explicitement ici pour pouvoir les attribuer dès cette migration.
    conteneurs_config = global_apps.get_app_config('conteneurs')
    create_permissions(conteneurs_config, apps=apps, verbosity=0)

    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    groupe, _ = Group.objects.get_or_create(name='Comptable')
    permissions = Permission.objects.filter(
        content_type__app_label='conteneurs',
        codename__in=['can_valider_paiement', 'view_dossier'],
    )
    groupe.permissions.set(permissions)


def supprimer_groupe_comptable(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='Comptable').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('conteneurs', '0017_alter_dossier_options_dossier_commentaire_paiement_and_more'),
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(creer_groupe_comptable, supprimer_groupe_comptable),
    ]
