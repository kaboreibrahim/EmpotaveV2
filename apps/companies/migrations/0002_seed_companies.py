from django.db import migrations


COMPANIES = [
    {"nom": "Oils of Africa", "slug": "oils-of-africa", "couleur": "#00450d"},
    {"nom": "Africa Newport Logistics", "slug": "africa-newport-logistics", "couleur": "#0b4f6c"},
    {"nom": "OTL & Bulk Liquid", "slug": "otl-bulk-liquid", "couleur": "#7a3b12"},
]


def seed_companies(apps, schema_editor):
    Company = apps.get_model('companies', 'Company')
    for data in COMPANIES:
        Company.objects.get_or_create(slug=data["slug"], defaults=data)


def unseed_companies(apps, schema_editor):
    Company = apps.get_model('companies', 'Company')
    Company.objects.filter(slug__in=[c["slug"] for c in COMPANIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_companies, unseed_companies),
    ]
