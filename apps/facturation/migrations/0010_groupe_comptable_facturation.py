"""Donne au groupe "Comptable" l'accès complet à la facturation (voir, créer,
modifier, supprimer, valider, envoyer)."""
from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.db import migrations


def _permissions_facture(apps):
    # Permissions créées d'habitude après toutes les migrations (post_migrate) :
    # on les génère ici pour pouvoir les attribuer tout de suite (cf. conteneurs 0018).
    create_permissions(global_apps.get_app_config('facturation'), apps=apps, verbosity=0)
    Permission = apps.get_model('auth', 'Permission')
    return Permission.objects.filter(content_type__app_label='facturation', content_type__model='facture')


def ajouter(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    groupe, _ = Group.objects.get_or_create(name='Comptable')
    groupe.permissions.add(*_permissions_facture(apps))


def retirer(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    groupe = Group.objects.filter(name='Comptable').first()
    if groupe:
        groupe.permissions.remove(*_permissions_facture(apps))


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0009_permissions_facture'),
        ('conteneurs', '0018_groupe_comptable'),
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(ajouter, retirer),
    ]
