from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0025_songcomment_parent_threading'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationpreferences',
            name='notify_release_reminders',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificationpreferences',
            name='release_reminder_days',
            field=models.PositiveSmallIntegerField(default=3),
        ),
    ]
