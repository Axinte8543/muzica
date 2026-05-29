from django.db import migrations, models


def backfill_listalbum_positions(apps, schema_editor):
    ListAlbum = apps.get_model('interactions', 'ListAlbum')

    # Set position per list based on added_at (oldest first).
    list_ids = (
        ListAlbum.objects.order_by()
        .values_list('list_id', flat=True)
        .distinct()
    )

    for list_id in list_ids:
        items = (
            ListAlbum.objects.filter(list_id=list_id)
            .order_by('added_at', 'id')
            .only('id')
        )
        for idx, item in enumerate(items, start=1):
            ListAlbum.objects.filter(id=item.id).update(position=idx)


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0012_albumlike'),
    ]

    operations = [
        migrations.AddField(
            model_name='list',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='listalbum',
            name='position',
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.RunPython(backfill_listalbum_positions, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='listalbum',
            options={'ordering': ['position', 'id']},
        ),
    ]
