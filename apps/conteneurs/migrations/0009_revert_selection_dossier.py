# Annule la migration 0008_selection_dossier : recrée les 5 champs photo sur
# ConteneurBase, y recopie les photos depuis SelectionDossier (propagées à
# tous les conteneurs d'un même dossier, car les valeurs individuelles par
# conteneur ont été physiquement supprimées par 0008 et ne sont plus
# récupérables telles quelles), puis supprime le modèle SelectionDossier.

from django.db import migrations, models


def restaurer_photos_sur_conteneurs(apps, schema_editor):
    ConteneurBase = apps.get_model('conteneurs', 'ConteneurBase')
    SelectionDossier = apps.get_model('conteneurs', 'SelectionDossier')

    for selection in SelectionDossier.objects.all():
        ConteneurBase.objects.filter(dossier=selection.dossier).update(
            photo_devant=selection.photo_avant,
            photo_derriere=selection.photo_arriere,
            photo_interieur=selection.photo_interieure,
            photo_lateral_droit=selection.photo_laterale_droite,
            photo_lateral_gauche=selection.photo_laterale_gauche,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('conteneurs', '0008_selection_dossier'),
    ]

    operations = [
        migrations.AddField(
            model_name='conteneurbase',
            name='photo_devant',
            field=models.ImageField(blank=True, null=True, upload_to='conteneurs/devant/'),
        ),
        migrations.AddField(
            model_name='conteneurbase',
            name='photo_derriere',
            field=models.ImageField(blank=True, null=True, upload_to='conteneurs/derriere/'),
        ),
        migrations.AddField(
            model_name='conteneurbase',
            name='photo_interieur',
            field=models.ImageField(blank=True, null=True, upload_to='conteneurs/interieur/'),
        ),
        migrations.AddField(
            model_name='conteneurbase',
            name='photo_lateral_droit',
            field=models.ImageField(blank=True, null=True, upload_to='conteneurs/lateral_droit/'),
        ),
        migrations.AddField(
            model_name='conteneurbase',
            name='photo_lateral_gauche',
            field=models.ImageField(blank=True, null=True, upload_to='conteneurs/lateral_gauche/'),
        ),
        migrations.RunPython(restaurer_photos_sur_conteneurs, noop_reverse),
        migrations.RemoveField(
            model_name='selectiondossier',
            name='agent_selection',
        ),
        migrations.RemoveField(
            model_name='selectiondossier',
            name='dossier',
        ),
        migrations.DeleteModel(
            name='SelectionDossier',
        ),
    ]
