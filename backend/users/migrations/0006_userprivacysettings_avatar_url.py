                                               

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_emailchangerequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprivacysettings',
            name='avatar_url',
            field=models.URLField(blank=True, null=True),
        ),
    ]
