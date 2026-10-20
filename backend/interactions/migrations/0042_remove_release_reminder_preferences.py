from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0041_artistrating'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='notificationpreferences',
            name='notify_release_reminders',
        ),
        migrations.RemoveField(
            model_name='notificationpreferences',
            name='release_reminder_days',
        ),
    ]
