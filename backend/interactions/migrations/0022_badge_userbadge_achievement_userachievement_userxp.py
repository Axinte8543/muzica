                                                           

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0021_notificationpreferences_notify_mentions_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(db_index=True, max_length=50, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('emoji', models.CharField(default='🏆', max_length=10)),
                ('category', models.CharField(choices=[('explorer', 'Music Explorer'), ('critic', 'Critic'), ('social', 'Social Butterfly'), ('activity', 'Activity Tracker'), ('collector', 'Collector'), ('milestone', 'Milestone')], max_length=20)),
                ('rarity', models.CharField(choices=[('common', 'Common'), ('uncommon', 'Uncommon'), ('rare', 'Rare'), ('epic', 'Epic'), ('legendary', 'Legendary')], default='common', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['category', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Achievement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(db_index=True, max_length=50, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('emoji', models.CharField(default='⭐', max_length=10)),
                ('type', models.CharField(choices=[('streak', 'Streak Achievement'), ('milestone', 'Milestone Achievement'), ('social', 'Social Achievement'), ('discovery', 'Discovery Achievement')], max_length=20)),
                ('target', models.PositiveIntegerField()),
                ('points', models.PositiveIntegerField(default=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['type', 'name'],
            },
        ),
        migrations.CreateModel(
            name='UserXP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_xp', models.PositiveIntegerField(default=0)),
                ('level', models.PositiveIntegerField(default=1)),
                ('current_level_xp', models.PositiveIntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user_xp', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User XP',
                'verbose_name_plural': 'User XP',
            },
        ),
        migrations.CreateModel(
            name='UserBadge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('earned_at', models.DateTimeField(auto_now_add=True)),
                ('progress', models.PositiveIntegerField(default=0)),
                ('target', models.PositiveIntegerField(default=0)),
                ('badge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='earned_by', to='interactions.badge')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='badges_earned', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-earned_at'],
                'unique_together': {('user', 'badge')},
            },
        ),
        migrations.CreateModel(
            name='UserAchievement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('progress', models.PositiveIntegerField(default=0)),
                ('unlocked_at', models.DateTimeField(blank=True, null=True)),
                ('is_completed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('achievement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unlocked_by', to='interactions.achievement')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='achievements_unlocked', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-unlocked_at', '-updated_at'],
                'unique_together': {('user', 'achievement')},
            },
        ),
        migrations.AddIndex(
            model_name='badge',
            index=models.Index(fields=['code'], name='interactions_badge_code_idx'),
        ),
        migrations.AddIndex(
            model_name='badge',
            index=models.Index(fields=['category'], name='interactions_badge_category_idx'),
        ),
        migrations.AddIndex(
            model_name='achievement',
            index=models.Index(fields=['code'], name='interactions_achievement_code_idx'),
        ),
        migrations.AddIndex(
            model_name='achievement',
            index=models.Index(fields=['type'], name='interactions_achievement_type_idx'),
        ),
        migrations.AddIndex(
            model_name='userbadge',
            index=models.Index(fields=['user', '-earned_at'], name='interactions_userbadge_user_earned_at_idx'),
        ),
        migrations.AddIndex(
            model_name='userbadge',
            index=models.Index(fields=['badge', '-earned_at'], name='interactions_userbadge_badge_earned_at_idx'),
        ),
        migrations.AddIndex(
            model_name='userachievement',
            index=models.Index(fields=['user', 'is_completed'], name='interactions_userachievement_user_completed_idx'),
        ),
        migrations.AddIndex(
            model_name='userachievement',
            index=models.Index(fields=['achievement', 'is_completed'], name='interactions_userachievement_achievement_completed_idx'),
        ),
        migrations.AddIndex(
            model_name='userachievement',
            index=models.Index(fields=['user', '-unlocked_at'], name='interactions_userachievement_user_unlocked_at_idx'),
        ),
    ]
