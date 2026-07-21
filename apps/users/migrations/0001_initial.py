import uuid
import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    operations = [
        migrations.CreateModel(
            name='Users',
            fields=[
                ('id',             models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password',       models.CharField(max_length=128, verbose_name='password')),
                ('last_login',     models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser',   models.BooleanField(default=False)),
                ('username',       models.CharField(error_messages={'unique': 'A user with that username already exists.'}, max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()])),
                ('first_name',     models.CharField(blank=True, max_length=150)),
                ('last_name',      models.CharField(blank=True, max_length=150)),
                ('email',          models.EmailField(blank=True, max_length=254)),
                ('is_staff',       models.BooleanField(default=False)),
                ('is_active',      models.BooleanField(default=True)),
                ('date_joined',    models.DateTimeField(default=django.utils.timezone.now)),
                ('deleted',        models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('numero',         models.CharField(blank=True, max_length=20, null=True)),
                ('photo',          models.ImageField(blank=True, null=True, upload_to='users/photos/')),
                ('date_created',   models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('is_verified',    models.BooleanField(default=False)),
                ('user_type',      models.CharField(choices=[('agent_selection', 'Agent de Sélection'), ('agent_acconage', 'Agent Habillage & Empotage'), ('personel', 'Personel'), ('client', 'Client')], max_length=20)),
                ('is_online',      models.BooleanField(default=False)),
                ('groups',         models.ManyToManyField(blank=True, related_name='users_otl_set', to='auth.group')),
                ('user_permissions', models.ManyToManyField(blank=True, related_name='users_otl_permissions_set', to='auth.permission')),
            ],
            options={'verbose_name': 'Utilisateur', 'verbose_name_plural': 'Utilisateurs', 'abstract': False},
            managers=[('objects', django.contrib.auth.models.UserManager())],
        ),
        migrations.CreateModel(
            name='CodeVerication',
            fields=[
                ('Id_Verication', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user',          models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='users.users')),
                ('code',          models.CharField(max_length=6)),
                ('date_created',  models.DateTimeField(auto_now_add=True)),
                ('typecode',      models.CharField(choices=[('rest', 'Reset'), ('forgat', 'Forgot'), ('validate', 'Validate')], max_length=10)),
            ],
            options={'verbose_name': 'Code de vérification'},
        ),
        migrations.CreateModel(
            name='Personel',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('user',         models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='client', to='users.users')),
            ],
            options={'verbose_name': 'Personnel interne', 'verbose_name_plural': 'Personnel interne', 'abstract': False},
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('user',         models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='agent_selection', to='users.users')),
            ],
            options={'verbose_name': 'Client', 'verbose_name_plural': 'Clients', 'abstract': False},
        ),
        migrations.CreateModel(
            name='Agent_selection',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('user',         models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='agent_empotage', to='users.users')),
            ],
            options={'verbose_name': 'Agent de sélection', 'verbose_name_plural': 'Agents de sélection', 'abstract': False},
        ),
        migrations.CreateModel(
            name='Agent_empotage',
            fields=[
                ('deleted',            models.DateTimeField(db_index=True, editable=False, null=True)),
                ('deleted_by_cascade', models.BooleanField(default=False, editable=False)),
                ('id',           models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('user',         models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='personel', to='users.users')),
            ],
            options={'verbose_name': 'Agent d\'empotage', 'verbose_name_plural': 'Agents d\'empotage', 'abstract': False},
        ),
        
        
    ]
