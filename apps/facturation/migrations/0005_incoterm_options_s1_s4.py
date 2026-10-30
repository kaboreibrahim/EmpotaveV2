from django.db import migrations, models

# Ancien code d'incoterm -> nouvelle option
CORRESPONDANCE = {"EXW": "S1", "FOB": "S3", "CFR": "S4", "DDP": "S4"}


def convertir_incoterms(apps, schema_editor):
    """Reporte l'incoterm de chaque facture (y compris supprimées) sur l'option S1 à S4."""
    Facture = apps.get_model("facturation", "Facture")
    for facture in Facture.objects.select_related("incoterm"):
        facture.option_incoterm = CORRESPONDANCE.get(facture.incoterm.code.upper(), "S1")
        facture.save(update_fields=["option_incoterm"])


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0004_ordre_lignes'),
    ]

    operations = [
        migrations.AddField(
            model_name='facture',
            name='option_incoterm',
            field=models.CharField(max_length=2, default='S1'),
            preserve_default=False,
        ),
        migrations.RunPython(convertir_incoterms, migrations.RunPython.noop),
        migrations.RemoveField(model_name='facture', name='incoterm'),
        migrations.RenameField(model_name='facture', old_name='option_incoterm', new_name='incoterm'),
        migrations.AlterField(
            model_name='facture',
            name='incoterm',
            field=models.CharField(
                max_length=2,
                choices=[
                    ('S1', 'S1 — EXW (Départ entrepôt Oils of Africa)'),
                    ('S2', 'S2 — EXW + Assistance technique'),
                    ('S3', 'S3 — FOB (Free On Board)'),
                    ('S4', 'S4 — CFR (Cost and Freight)'),
                ],
            ),
        ),
        migrations.DeleteModel(name='Incoterm'),
    ]
