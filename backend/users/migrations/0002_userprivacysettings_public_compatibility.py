from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('users', '0001_initial'),
	]

	operations = [
		migrations.AddField(
			model_name='userprivacysettings',
			name='public_compatibility',
			field=models.BooleanField(default=True),
		),
	]