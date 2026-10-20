from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q

from interactions.models import AlbumRating, AlbumReview, FavoriteAlbum, FavoriteSong, ListAlbum, SongComment, SongRating
from music.models import Album, Artist, Song, SongFeature


PLACEHOLDER_DATE = date(1970, 1, 1)


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().split()).lower()


def _album_score(album: Album) -> tuple[int, int, int, int, int, int, int]:
    return (
        1 if album.release_date and album.release_date != PLACEHOLDER_DATE else 0,
        1 if album.cover_url else 0,
        1 if album.spotify_id else 0,
        1 if album.musicbrainz_id else 0,
        1 if album.is_approved else 0,
        album.songs.count(),
        -album.id,
    )


def _song_score(song: Song) -> tuple[int, int, int, int, int, int]:
    interaction_count = (
        SongRating.objects.filter(song=song).count()
        + SongComment.objects.filter(song=song).count()
        + FavoriteSong.objects.filter(song=song).count()
    )
    return (
        interaction_count,
        1 if song.spotify_id else 0,
        1 if song.musicbrainz_id else 0,
        1 if song.duration_seconds else 0,
        1 if song.is_approved else 0,
        -song.id,
    )


def _album_has_interactions(album: Album) -> bool:
    return (
        AlbumRating.objects.filter(album=album).exists()
        or AlbumReview.objects.filter(album=album).exists()
        or FavoriteAlbum.objects.filter(album=album).exists()
        or ListAlbum.objects.filter(album=album).exists()
    )


def _song_has_interactions(song: Song) -> bool:
    return (
        SongRating.objects.filter(song=song).exists()
        or SongComment.objects.filter(song=song).exists()
        or FavoriteSong.objects.filter(song=song).exists()
    )


class Command(BaseCommand):
    help = "Conservative catalog cleanup: empty duplicate artists, weak duplicate albums, and safe duplicate songs."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        deleted_empty_artists = 0
        merged_albums = 0
        deleted_songs = 0
        unapproved_empty_albums = 0
        unapproved_weak_lastfm_songs = 0
        skipped_album_groups = 0

        with transaction.atomic():
            empty_albums = (
                Album.objects.annotate(songs_count=Count("songs", distinct=True))
                .filter(is_approved=True, songs_count=0)
            )
            for album in empty_albums:
                if dry_run:
                    self.stdout.write(f"[dry-run] unapprove empty album: {album.title} ({album.id})")
                else:
                    album.is_approved = False
                    album.save(update_fields=["is_approved"])
                unapproved_empty_albums += 1

            weak_lastfm_songs = Song.objects.filter(
                is_approved=True,
                album__isnull=True,
                duration_seconds=0,
                track_number__isnull=True,
                slug__icontains="lastfm",
            ).filter(
                Q(spotify_id__isnull=True) | Q(spotify_id="")
            ).filter(
                Q(musicbrainz_id__isnull=True) | Q(musicbrainz_id="")
            )
            for song in weak_lastfm_songs:
                if _song_has_interactions(song):
                    continue
                if dry_run:
                    self.stdout.write(f"[dry-run] unapprove weak Last.fm song: {song.title} ({song.id})")
                else:
                    song.is_approved = False
                    song.save(update_fields=["is_approved"])
                unapproved_weak_lastfm_songs += 1

            duplicate_names = (
                Artist.objects.values("name")
                .annotate(count=Count("id"))
                .filter(count__gt=1)
                .values_list("name", flat=True)
            )
            for name in duplicate_names:
                artists = list(Artist.objects.filter(name=name).order_by("id"))
                for artist in artists:
                    if artist.albums.exists() or artist.songs.exists():
                        continue
                    if artist.is_approved and (artist.spotify_id or artist.musicbrainz_id):
                        continue
                    if dry_run:
                        self.stdout.write(f"[dry-run] delete empty duplicate artist: {artist.name} ({artist.id})")
                    else:
                        artist.delete()
                    deleted_empty_artists += 1

            duplicate_album_groups = (
                Album.objects.values("artist_id", "title")
                .annotate(count=Count("id"))
                .filter(count__gt=1)
            )
            for group in duplicate_album_groups:
                albums = list(
                    Album.objects.filter(artist_id=group["artist_id"], title=group["title"])
                    .select_related("artist")
                    .order_by("id")
                )
                if len(albums) < 2:
                    continue

                albums.sort(key=_album_score, reverse=True)
                canonical = albums[0]
                duplicates = albums[1:]
                weak_duplicates = [
                    album
                    for album in duplicates
                    if album.release_date == PLACEHOLDER_DATE
                    or (not album.spotify_id and not album.musicbrainz_id and not _album_has_interactions(album))
                ]
                if not weak_duplicates:
                    skipped_album_groups += 1
                    continue

                for album in weak_duplicates:
                    if dry_run:
                        self.stdout.write(
                            f"[dry-run] merge album duplicate: {album.artist.name} - {album.title} ({album.id}) -> {canonical.id}"
                        )
                        merged_albums += 1
                        continue

                    for genre in album.genres.all():
                        canonical.genres.add(genre)

                    dirty_fields: list[str] = []
                    if not canonical.cover_url and album.cover_url:
                        canonical.cover_url = album.cover_url
                        dirty_fields.append("cover_url")
                    if canonical.release_date == PLACEHOLDER_DATE and album.release_date != PLACEHOLDER_DATE:
                        canonical.release_date = album.release_date
                        dirty_fields.append("release_date")
                    if not canonical.spotify_id and album.spotify_id:
                        canonical.spotify_id = album.spotify_id
                        dirty_fields.append("spotify_id")
                    if not canonical.spotify_url and album.spotify_url:
                        canonical.spotify_url = album.spotify_url
                        dirty_fields.append("spotify_url")
                    if not canonical.musicbrainz_id and album.musicbrainz_id:
                        canonical.musicbrainz_id = album.musicbrainz_id
                        dirty_fields.append("musicbrainz_id")
                    if not canonical.is_approved and album.is_approved:
                        canonical.is_approved = True
                        dirty_fields.append("is_approved")
                    if dirty_fields:
                        canonical.save(update_fields=dirty_fields)

                    for song in Song.objects.filter(album=album):
                        if Song.objects.filter(
                            album=canonical,
                            artist=song.artist,
                            title__iexact=song.title,
                        ).exists() and not _song_has_interactions(song):
                            song.delete()
                        else:
                            song.album = canonical
                            song.save(update_fields=["album"])
                    album.delete()
                    merged_albums += 1

            duplicate_song_groups = (
                Song.objects.values("artist_id", "album_id", "title")
                .annotate(count=Count("id"))
                .filter(count__gt=1)
            )
            for group in duplicate_song_groups:
                songs = list(
                    Song.objects.filter(
                        artist_id=group["artist_id"],
                        album_id=group["album_id"],
                        title=group["title"],
                    ).order_by("id")
                )
                if len(songs) < 2:
                    continue
                songs.sort(key=_song_score, reverse=True)
                canonical = songs[0]
                for song in songs[1:]:
                    if _song_has_interactions(song):
                        continue
                    if dry_run:
                        self.stdout.write(f"[dry-run] delete duplicate song: {song.title} ({song.id}) -> {canonical.id}")
                        deleted_songs += 1
                        continue
                    for genre in song.genres.all():
                        canonical.genres.add(genre)
                    SongFeature.objects.filter(song=song).update(song=canonical)
                    song.delete()
                    deleted_songs += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalog cleanup {'dry-run' if dry_run else 'updated'}: "
                f"deleted_empty_artists={deleted_empty_artists} "
                f"merged_albums={merged_albums} deleted_songs={deleted_songs} "
                f"unapproved_empty_albums={unapproved_empty_albums} "
                f"unapproved_weak_lastfm_songs={unapproved_weak_lastfm_songs} "
                f"skipped_album_groups={skipped_album_groups}"
            )
        )
