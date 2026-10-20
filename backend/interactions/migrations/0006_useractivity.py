                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0005_friendrequest'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(choices=[('rate_album', 'Rate album'), ('review_album', 'Review album'), ('follow_artist', 'Follow artist'), ('create_list', 'Create list')], max_length=30)),
                ('target_id', models.IntegerField(blank=True, null=True)),
                ('target_name', models.CharField(blank=True, max_length=255)),
                ('rating', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['-created_at'], name='interaction_created_3a4b31_idx'), models.Index(fields=['actor', '-created_at'], name='interaction_actor_i_efa7e2_idx'), models.Index(fields=['activity_type', '-created_at'], name='interaction_activit_c0c83d_idx')],
            },
        ),
    ]
