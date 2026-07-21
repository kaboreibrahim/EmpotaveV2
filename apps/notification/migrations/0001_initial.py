import django.db.models.deletion
import django.utils.timezone
import django_lifecycle.mixins
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('users', '0001_initial'),
    ]
    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('user',         models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='users.users')),
                ('message',      models.TextField()),
                ('is_read',      models.BooleanField(default=False)),
            ],
            options={'verbose_name': 'Notification', 'ordering': ['-date_created'], 'abstract': False},
            bases=(django_lifecycle.mixins.LifecycleModelMixin, models.Model),
        ),
    ]
