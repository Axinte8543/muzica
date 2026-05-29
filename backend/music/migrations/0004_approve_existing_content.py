from django.db import migrations


def forwards(apps, schema_editor):
	Artist = apps.get_model('music', 'Artist')
	Album = apps.get_model('music', 'Album')
	Song = apps.get_model('music', 'Song')

	Artist.objects.filter(is_approved=False).update(is_approved=True)
	Album.objects.filter(is_approved=False).update(is_approved=True)
	Song.objects.filter(is_approved=False).update(is_approved=True)


def backwards(apps, schema_editor):
	Artist = apps.get_model('music', 'Artist')
	Album = apps.get_model('music', 'Album')
	Song = apps.get_model('music', 'Song')

	Artist.objects.update(is_approved=False)
	Album.objects.update(is_approved=False)
	Song.objects.update(is_approved=False)


class Migration(migrations.Migration):

	dependencies = [
		('music', '0003_add_approval_flags'),
	]

	operations = [
		migrations.RunPython(forwards, backwards),
	]
