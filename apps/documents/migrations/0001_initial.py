import uuid
import django.db.models.deletion
import django.utils.timezone
import django_lifecycle.mixins
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('conteneurs', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='TypeDocument',
            fields=[
                ('Id_TypeDocument', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('type_document',   models.CharField(max_length=100, unique=True)),
            ],
            options={'verbose_name': 'Type de document', 'ordering': ['type_document']},
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',             models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created',   models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('dossier',        models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='conteneurs.dossier')),
                ('type_document',  models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='documents.typedocument')),
                ('fichier',        models.FileField(upload_to='documents/%Y/%m/%d/')),
                ('date_modifier',  models.DateTimeField(auto_now=True)),
                ('statut',         models.CharField(choices=[('Terminé', 'Terminé'), ('EnAttente', 'En Attente')], default='EnAttente', max_length=10)),
            ],
            options={'verbose_name': 'Document', 'ordering': ['-date_created'], 'abstract': False},
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
