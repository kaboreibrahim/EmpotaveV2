from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturation', '0007_incoterm_options_ss1_ss4'),
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
                    ('SS5', 'SS5 — CIF (Cost, Insurance and Freight)'),
                ],
            ),
        ),
    ]
