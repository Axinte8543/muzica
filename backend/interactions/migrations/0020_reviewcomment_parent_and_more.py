                                               

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0019_listtag_list_tags_moderationreport_albumreviewdraft_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='reviewcomment',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='interactions.reviewcomment'),
        ),
        migrations.AlterField(
            model_name='useractivity',
            name='activity_type',
            field=models.CharField(choices=[('listen_album', 'Listen album'), ('rate_album', 'Rate album'), ('review_album', 'Review album'), ('follow_artist', 'Follow artist'), ('create_list', 'Create list'), ('list_add_album', 'Add album to list')], max_length=30),
        ),
        migrations.AddIndex(
            model_name='reviewcomment',
            index=models.Index(fields=['parent', 'created_at'], name='interaction_parent__c52700_idx'),
        ),
    ]
