from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("music", "0002_song_artist_and_single_support"),
        ("interactions", "0006_useractivity"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AlbumListen",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("listened_at", models.DateTimeField(auto_now_add=True)),
                (
                    "listened_date",
                    models.DateField(default=django.utils.timezone.localdate, db_index=True),
                ),
                (
                    "album",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="listens",
                        to="music.album",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="album_listens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-listened_at"],
            },
        ),
        migrations.AddIndex(
            model_name="albumlisten",
            index=models.Index(fields=["album", "-listened_at"], name="interaction_album_i_270e35_idx"),
        ),
        migrations.AddIndex(
            model_name="albumlisten",
            index=models.Index(fields=["user", "-listened_at"], name="interaction_user_id_10e8ae_idx"),
        ),
        migrations.AddConstraint(
            model_name="albumlisten",
            constraint=models.UniqueConstraint(
                fields=("user", "album", "listened_date"),
                name="unique_album_listen_per_day",
            ),
        ),
    ]
