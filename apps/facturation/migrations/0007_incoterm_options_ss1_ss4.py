from django.db import migrations, models


def renommer_options(apps, schema_editor):
    """S1 à S4 -> SS1 à SS4 (y compris factures supprimées)."""
    Facture = apps.get_model("facturation", "Facture")
    for ancien in ("S1", "S2", "S3", "S4"):
        Facture.objects.filter(incoterm=ancien).update(incoterm="S" + ancien)


def restaurer_options(apps, schema_editor):
    Facture = apps.get_model("facturation", "Facture")
    for nouveau in ("SS1", "SS2", "SS3", "SS4"):
        Facture.objects.filter(incoterm=nouveau).update(incoterm=nouveau[1:])


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0006_champs_optionnels_s1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facture',
            name='incoterm',
            field=models.CharField(
                max_length=3,
                choices=[
                    ('SS1', 'SS1 — EXW (Départ entrepôt Oils of Africa)'),
                    ('SS2', 'SS2 — EXW + Assistance technique'),
                    ('SS3', 'SS3 — FOB (Free On Board)'),
                    ('SS4', 'SS4 — CFR (Cost and Freight)'),
                ],
            ),
        ),
        migrations.RunPython(renommer_options, restaurer_options),
    ]
