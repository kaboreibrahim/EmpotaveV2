"""
apps/conteneurs/migrations/0013_conteneur_mixin_refactor_pivot_drop.py

Suite de 0012 : supprime le pivot OneToOne (ISOTanks.iso, Flexitanks.conteneur)
et la table ConteneurBase elle-même, une fois le backfill des données terminé.

Séparée de 0012 dans sa propre transaction : Postgres refuse un ALTER TABLE
sur une table encore concernée par des événements de trigger en attente
(FK ON DELETE) dans la même transaction qu'un DELETE précédent (ici, la
suppression des 2 lignes orphelines faite par le RunPython de 0012).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('conteneurs', '0012_conteneur_mixin_refactor'),
    ]

    operations = [
        # --- Fin du pivot OneToOne -------------------------------------------
        migrations.RemoveField(model_name='isotanks', name='iso'),
        migrations.RemoveField(model_name='flexitanks', name='conteneur'),

        # --- Options de modèle alignées sur ConteneurBase (tri par référence) --
        migrations.AlterModelOptions(
            name='isotanks',
            options={'ordering': ['reference'], 'verbose_name': 'ISO Tank', 'verbose_name_plural': 'ISO Tanks'},
        ),
        migrations.AlterModelOptions(
            name='flexitanks',
            options={'ordering': ['reference'], 'verbose_name': 'Flexitank', 'verbose_name_plural': 'Flexitanks'},
        ),

        # --- Suppression de la table pivot ------------------------------------
        migrations.DeleteModel(name='ConteneurBase'),
    ]
