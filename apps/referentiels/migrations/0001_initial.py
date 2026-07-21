import uuid
import django.db.models.deletion
import django.utils.timezone
import django_lifecycle.mixins
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Pays',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('nom',          models.CharField(max_length=100, unique=True)),
            ],
            options={'verbose_name': 'Pays', 'ordering': ['nom'], 'abstract': False},
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='Commodite',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('nom',          models.CharField(max_length=100)),
                ('icon',         models.ImageField(blank=True, null=True, upload_to='commodites/icons/')),
                ('sig',          models.CharField(blank=True, max_length=20, null=True, verbose_name='Sigle')),
                ('Id_Pays',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commodites', to='referentiels.pays')),
            ],
            options={'verbose_name': 'Commodité', 'ordering': ['nom'], 'abstract': False},
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='POL',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('nom',          models.CharField(max_length=100)),
                ('lieu',         models.CharField(max_length=200)),
                ('Id_Pays',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pols', to='referentiels.pays')),
            ],
            options={'verbose_name': 'Port de chargement (POL)', 'abstract': False},
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='POD',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('nom',          models.CharField(max_length=100)),
                ('lieu',         models.CharField(max_length=200)),
                ('Id_Pays',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pods', to='referentiels.pays')),
            ],
            options={'verbose_name': 'Port de déchargement (POD)', 'abstract': False},
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='CompagnieMaritime',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('nom',          models.CharField(max_length=100)),
                ('lieu',         models.CharField(max_length=200)),
                ('Id_Pays',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='compagnies_maritimes', to='referentiels.pays')),
            ],
            options={'verbose_name': 'Compagnie maritime', 'abstract': False},
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='SiteSelection',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('nom',          models.CharField(max_length=100)),
                ('contact',      models.CharField(max_length=50)),
                ('lieu',         models.CharField(max_length=200)),
                ('Id_Pays',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sites_selection', to='referentiels.pays')),
            ],
            options={'verbose_name': "Site de sélection", 'abstract': False},
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='SiteEmpotage',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('nom',          models.CharField(max_length=100)),
                ('contact',      models.CharField(max_length=50)),
                ('lieu',         models.CharField(max_length=200)),
                ('Id_Pays',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sites_empotage', to='referentiels.pays')),
            ],
            options={'verbose_name': "Site d'empotage", 'abstract': False},
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
