                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0039_achievementunlock_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserSuspension',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(choices=[('content_violation', 'Content Violation'), ('spam', 'Spam'), ('abuse', 'Abuse'), ('harassment', 'Harassment'), ('false_info', 'False Information'), ('other', 'Other')], default='other', max_length=50)),
                ('duration_type', models.CharField(choices=[('permanent', 'Permanent'), ('one_week', '1 Week'), ('one_month', '1 Month'), ('three_months', '3 Months'), ('custom', 'Custom')], default='one_month', max_length=20)),
                ('suspended_at', models.DateTimeField(auto_now_add=True)),
                ('suspended_until', models.DateTimeField(blank=True, null=True)),
                ('reason_detail', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('appeal_at', models.DateTimeField(blank=True, null=True)),
                ('appeal_reason', models.TextField(blank=True)),
                ('appealed_by_user', models.BooleanField(default=False)),
                ('related_report', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suspensions', to='interactions.moderationreport')),
                ('suspended_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suspensions_issued', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suspensions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-suspended_at', '-id'],
                'indexes': [models.Index(fields=['user', '-suspended_at'], name='interaction_user_id_f970be_idx'), models.Index(fields=['is_active', '-suspended_at'], name='interaction_is_acti_44a2ba_idx')],
            },
        ),
    ]
