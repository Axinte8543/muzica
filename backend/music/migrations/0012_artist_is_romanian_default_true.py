from django.db import migrations, models


def mark_all_artists_romanian(apps, schema_editor):
	Artist = apps.get_model('music', 'Artist')
	Artist.objects.filter(is_romanian=False).update(is_romanian=True)


class Migration(migrations.Migration):

	dependencies = [
		('music', '0011_album_mb_primary_type_album_mb_secondary_types'),
	]

	operations = [
		migrations.AlterField(
			model_name='artist',
			name='is_romanian',
			field=models.BooleanField(default=True),
		),
		migrations.RunPython(mark_all_artists_romanian, migrations.RunPython.noop),
	]
