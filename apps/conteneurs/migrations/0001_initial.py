import decimal
import uuid

import django.db.models.deletion
import django.utils.timezone
import django_lifecycle.mixins
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('referentiels', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dossier',
            fields=[
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('statut', models.CharField(choices=[('en_attente', 'En Attente'), ('selection_en_cours', 'SÃ©lection en cours'), ('empotage_en_cours', 'Empotage en cours'), ('dossier_termine', 'TerminÃ©'), ('annulÃ©', 'AnnulÃ©')], default='en_attente', max_length=25)),
                ('TRD', models.CharField(max_length=50, verbose_name='NumÃ©ro TRD')),
                ('projet', models.CharField(max_length=100)),
                ('Booking', models.CharField(max_length=100)),
                ('type_conteneur', models.CharField(choices=[('10_pieds', '10 Pieds'), ('20_pieds', '20 Pieds'), ('ISO_20_pieds', 'ISO Tank 20 Pieds'), ('40_pieds', '40 Pieds')], max_length=13)),
                ('date_de_selection', models.DateTimeField(blank=True, null=True)),
                ('date_de_empotage', models.DateTimeField(blank=True, null=True)),
                ('date_de_soumission_du_rapport', models.DateTimeField(blank=True, null=True)),
                ('date_de_fin_d_empotage', models.DateTimeField(blank=True, null=True)),
                ('Id_Agent_empotage', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dossiers', to='users.agent_empotage')),
                ('Id_Agent_selection', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dossiers', to='users.agent_selection')),
                ('Id_Commodite', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='referentiels.commodite')),
                ('Id_CompagnieMaritime', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='referentiels.compagniemaritime')),
                ('Id_POD', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='referentiels.pod')),
                ('Id_POL', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='referentiels.pol')),
                ('Id_Pays', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='referentiels.pays')),
                ('Id_Personel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dossiers', to='users.personel')),
                ('Id_SiteEmpotage', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='referentiels.siteempotage')),
                ('Id_SiteSelection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='referentiels.siteselection')),
                ('id_client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dossiers', to='users.client')),
            ],
            options={
                'verbose_name': 'Dossier',
                'verbose_name_plural': 'Dossiers',
                'ordering': ['-date_created'],
                'abstract': False,
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ConteneurBase',
            fields=[
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('statut', models.CharField(choices=[('non_empote', 'Non empotÃ©'), ('empote', 'EmpotÃ©')], default='non_empote', max_length=20)),
                ('reference', models.CharField(max_length=50, unique=True)),
                ('etat', models.CharField(choices=[('excellent', 'Excellent'), ('moyen', 'Moyen'), ('mauvais', 'Mauvais')], max_length=10)),
                ('photo_devant', models.ImageField(blank=True, null=True, upload_to='conteneurs/devant/')),
                ('photo_pendant', models.ImageField(blank=True, null=True, upload_to='conteneurs/pendant/')),
                ('photo_fin', models.ImageField(blank=True, null=True, upload_to='conteneurs/fin/')),
                ('photo_derriere', models.ImageField(blank=True, null=True, upload_to='conteneurs/derriere/')),
                ('photo_interieur', models.ImageField(blank=True, null=True, upload_to='conteneurs/interieur/')),
                ('photo_lateral_droit', models.ImageField(blank=True, null=True, upload_to='conteneurs/lateral_droit/')),
                ('photo_lateral_gauche', models.ImageField(blank=True, null=True, upload_to='conteneurs/lateral_gauche/')),
                ('Temerature', models.FloatField(blank=True, null=True, verbose_name='TempÃ©rature (Â°C)')),
                ('photo_plombs_oils', models.ImageField(blank=True, null=True, upload_to='conteneurs/plombs_oils/')),
                ('Plombs_oils', models.CharField(blank=True, help_text='NumÃ©ros de plombs huiles (sÃ©parÃ©s par virgule)', max_length=200, null=True)),
                ('pd', models.CharField(blank=True, max_length=100, null=True, verbose_name='PD')),
                ('poids_brute', models.DecimalField(blank=True, decimal_places=2, default=decimal.Decimal('0.00'), max_digits=10, null=True)),
                ('poids_equipements', models.DecimalField(blank=True, decimal_places=2, default=decimal.Decimal('0.00'), max_digits=10, null=True)),
                ('poids_net', models.DecimalField(blank=True, decimal_places=2, default=decimal.Decimal('0.00'), max_digits=10, null=True)),
                ('dossier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conteneurs', to='conteneurs.dossier')),
            ],
            options={
                'verbose_name': 'Conteneur',
                'verbose_name_plural': 'Conteneurs',
                'ordering': ['reference'],
                'abstract': False,
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='Flexitanks',
            fields=[
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('Numeroheatingpad', models.CharField(blank=True, max_length=50, null=True)),
                ('Photoheatingpad', models.ImageField(blank=True, null=True, upload_to='flexitanks/heatingpad/')),
                ('photoFlextank', models.ImageField(blank=True, null=True, upload_to='flexitanks/photos/')),
                ('numeroFlextank', models.CharField(blank=True, max_length=50, null=True)),
                ('plombs_amateur', models.CharField(blank=True, help_text='NumÃ©ros de plombs amateur (sÃ©parÃ©s par virgule)', max_length=200, null=True)),
                ('plombs_amateur_photo', models.ImageField(blank=True, null=True, upload_to='flexitanks/plombs_amateur/')),
                ('conteneur', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='flexitank', to='conteneurs.conteneurbase')),
            ],
            options={
                'verbose_name': 'Flexitank',
                'verbose_name_plural': 'Flexitanks',
                'abstract': False,
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ISOTanks',
            fields=[
                ('deleted', models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('plomb1', models.CharField(blank=True, max_length=50, null=True)),
                ('plomb2', models.CharField(blank=True, max_length=50, null=True)),
                ('plomb3', models.CharField(blank=True, max_length=50, null=True)),
                ('photoplomb1', models.ImageField(blank=True, null=True, upload_to='isotanks/plombs/')),
                ('photoplomb2', models.ImageField(blank=True, null=True, upload_to='isotanks/plombs/')),
                ('photoplomb3', models.ImageField(blank=True, null=True, upload_to='isotanks/plombs/')),
                ('conteneur', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='iso_tank', to='conteneurs.conteneurbase')),
            ],
            options={
                'verbose_name': 'ISO Tank',
                'verbose_name_plural': 'ISO Tanks',
                'abstract': False,
            },
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
