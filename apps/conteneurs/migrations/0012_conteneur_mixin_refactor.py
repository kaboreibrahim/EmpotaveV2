"""
apps/conteneurs/migrations/0012_conteneur_mixin_refactor.py

Éclate ConteneurBase (table pivot) en champs communs directement portés par
ISOTanks et Flexitanks : ConteneurBase devient un mixin abstrait côté code
(voir apps/conteneurs/models.py), donc sa table disparaît.

Deux lignes ConteneurBase sans aucune extension ISOTanks/Flexitanks liée
(FTAU205684-10, FTAU205684-20 — restes de soumissions qui ont échoué avant la
création de leur extension, bug corrigé par ce même refactor) sont
supprimées : aucune donnée exploitable à migrer pour elles.

Cette migration n'est pas raisonnablement réversible une fois appliquée
(la table ConteneurBase et les 2 lignes orphelines sont définitivement
supprimées) ; `migrations.RunPython.noop` est utilisé comme opération
inverse pour ne pas prétendre le contraire.
"""
from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models

import apps.common.fields

CHAMPS_COMMUNS = [
    'dossier_id', 'statut', 'reference', 'etat',
    'photo_debut', 'photo_pendant', 'photo_fin',
    'photo_devant', 'photo_derriere', 'photo_interieur',
    'photo_lateral_droit', 'photo_lateral_gauche',
    'Temerature', 'poids_net',
]


def migrer_donnees(apps, schema_editor):
    ConteneurBase = apps.get_model('conteneurs', 'ConteneurBase')
    ISOTanks = apps.get_model('conteneurs', 'ISOTanks')
    Flexitanks = apps.get_model('conteneurs', 'Flexitanks')

    ConteneurBase.objects.filter(iso_tank__isnull=True, flexitank__isnull=True).delete()

    for iso in ISOTanks.objects.select_related('iso').all():
        base = iso.iso
        for champ in CHAMPS_COMMUNS:
            setattr(iso, champ, getattr(base, champ))
        iso.save()

    for flexi in Flexitanks.objects.select_related('conteneur').all():
        base = flexi.conteneur
        for champ in CHAMPS_COMMUNS:
            setattr(flexi, champ, getattr(base, champ))
        flexi.save()


class Migration(migrations.Migration):

    dependencies = [
        ('conteneurs', '0011_alter_conteneurbase_photo_debut_and_more'),
    ]

    operations = [
        # --- 1. Champs communs ajoutés sur ISOTanks et Flexitanks ---------
        # (dossier/reference/etat en nullable temporairement, le temps du backfill)
        migrations.AddField(
            model_name='isotanks',
            name='dossier',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s', to='conteneurs.dossier'),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='statut',
            field=models.CharField(choices=[('non_empote', 'Non empoté'), ('empote', 'Empoté')], default='non_empote', max_length=20),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='reference',
            field=models.CharField(max_length=50, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='etat',
            field=models.CharField(choices=[('excellent', 'Excellent'), ('moyen', 'Moyen'), ('mauvais', 'Mauvais')], max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='photo_debut',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/debut/'),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='photo_pendant',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/pendant/'),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='photo_fin',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/fin/'),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='photo_devant',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/devant/'),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='photo_derriere',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/derriere/'),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='photo_interieur',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/interieur/'),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='photo_lateral_droit',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/lateral_droit/'),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='photo_lateral_gauche',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/lateral_gauche/'),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='Temerature',
            field=models.FloatField(blank=True, null=True, verbose_name='Température (°C)'),
        ),
        migrations.AddField(
            model_name='isotanks',
            name='poids_net',
            field=models.DecimalField(blank=True, decimal_places=2, default=Decimal('0.00'), max_digits=10, null=True),
        ),

        migrations.AddField(
            model_name='flexitanks',
            name='dossier',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s', to='conteneurs.dossier'),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='statut',
            field=models.CharField(choices=[('non_empote', 'Non empoté'), ('empote', 'Empoté')], default='non_empote', max_length=20),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='reference',
            field=models.CharField(max_length=50, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='etat',
            field=models.CharField(choices=[('excellent', 'Excellent'), ('moyen', 'Moyen'), ('mauvais', 'Mauvais')], max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='photo_debut',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/debut/'),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='photo_pendant',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/pendant/'),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='photo_fin',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/fin/'),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='photo_devant',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/devant/'),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='photo_derriere',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/derriere/'),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='photo_interieur',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/interieur/'),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='photo_lateral_droit',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/lateral_droit/'),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='photo_lateral_gauche',
            field=apps.common.fields.WebPImageField(blank=True, null=True, upload_to='conteneurs/lateral_gauche/'),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='Temerature',
            field=models.FloatField(blank=True, null=True, verbose_name='Température (°C)'),
        ),
        migrations.AddField(
            model_name='flexitanks',
            name='poids_net',
            field=models.DecimalField(blank=True, decimal_places=2, default=Decimal('0.00'), max_digits=10, null=True),
        ),

        # --- 2. Backfill des données depuis ConteneurBase ------------------
        migrations.RunPython(migrer_donnees, migrations.RunPython.noop),

        # --- 3. Contraintes finales (non-null, comme sur ConteneurBase) ----
        migrations.AlterField(
            model_name='isotanks',
            name='dossier',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s', to='conteneurs.dossier'),
        ),
        migrations.AlterField(
            model_name='isotanks',
            name='reference',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='isotanks',
            name='etat',
            field=models.CharField(choices=[('excellent', 'Excellent'), ('moyen', 'Moyen'), ('mauvais', 'Mauvais')], max_length=10),
        ),
        migrations.AlterField(
            model_name='flexitanks',
            name='dossier',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s', to='conteneurs.dossier'),
        ),
        migrations.AlterField(
            model_name='flexitanks',
            name='reference',
            field=models.CharField(max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name='flexitanks',
            name='etat',
            field=models.CharField(choices=[('excellent', 'Excellent'), ('moyen', 'Moyen'), ('mauvais', 'Mauvais')], max_length=10),
        ),
    ]
