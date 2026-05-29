from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0026_notificationpreferences_release_reminders'),
    ]

    operations = [
        migrations.AddField(
            model_name='moderationreport',
            name='resolution_reason',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='moderationreport',
            name='resolution_feedback',
            field=models.TextField(blank=True, default=''),
        ),
    ]
