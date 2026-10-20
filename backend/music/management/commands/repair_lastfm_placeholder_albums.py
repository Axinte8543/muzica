from __future__ import annotations

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils.text import slugify

from interactions.models import AlbumListen, AlbumRating, AlbumReview, FavoriteAlbum, ListAlbum
from music.lastfm import LastFMAPIError, LastFMClient
from music.models import Album, Song


PLACEHOLDER_DATE = date(1970, 1, 1)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _unique_slug(model, base: str) -> str:
    base_slug = slugify(_clean(base)) or "item"
    slug = base_slug
    suffix = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def _track_items(album_info: dict[str, Any]) -> list[dict[str, Any]]:
    tracks = ((album_info.get("tracks") or {}).get("track")) or []
    if isinstance(tracks, dict):
        tracks = [tracks]
    if not isinstance(tracks, list):
        return []
    return [track for track in tracks if isinstance(track, dict)]


def _has_album_interactions(album: Album) -> bool:
    return (
        AlbumRating.objects.filter(album=album).exists()
        or AlbumReview.objects.filter(album=album).exists()
        or AlbumListen.objects.filter(album=album).exists()
        or FavoriteAlbum.objects.filter(album=album).exists()
        or ListAlbum.objects.filter(album=album).exists()
    )


class Command(BaseCommand):
    help = "Repair Last.fm placeholder albums by importing tracklists or hiding empty fake albums."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Maximum albums to scan.")
        parser.add_argument("--dry-run", action="store_true", help="Show changes without saving.")
        parser.add_argument(
            "--hide-empty",
            action="store_true",
            help="Unapprove Last.fm placeholder albums that still have no songs after lookup.",
        )

    def handle(self, *args, **options):
        limit = max(0, int(options.get("limit") or 0))
        dry_run = bool(options.get("dry_run"))
        hide_empty = bool(options.get("hide_empty"))

        qs = (
            Album.objects.select_related("artist")
            .annotate(songs_count=Count("songs", distinct=True))
            .filter(is_approved=True, release_date=PLACEHOLDER_DATE, songs_count__lte=1)
            .order_by("artist__name", "title", "id")
        )
        if limit:
            qs = qs[:limit]

        client = LastFMClient()
        scanned = 0
        tracks_created = 0
        hidden_empty = 0
        failures = 0

        for album in qs:
            scanned += 1
            try:
                info = client.get_album_info(artist_name=album.artist.name, album_title=album.title)
            except LastFMAPIError as exc:
                failures += 1
                self.stdout.write(self.style.WARNING(f"Last.fm failed for {album.artist.name} - {album.title}: {exc}"))
                continue

            created_for_album = 0
            tracks = _track_items(info)
            if tracks:
                with transaction.atomic():
                    for index, track in enumerate(tracks, start=1):
                        title = _clean(track.get("name") or "")
                        if not title:
                            continue
                        if Song.objects.filter(album=album, title__iexact=title).exists():
                            continue
                        if dry_run:
                            created_for_album += 1
                            continue
                        Song.objects.create(
                            album=album,
                            artist=album.artist,
                            title=title,
                            slug=_unique_slug(Song, f"{album.artist.name}-{album.title}-{title}"),
                            track_number=index,
                            duration_seconds=0,
                            is_approved=True,
                        )
                        created_for_album += 1
                tracks_created += created_for_album
                if created_for_album:
                    self.stdout.write(f"{album.artist.name} - {album.title}: added tracks={created_for_album}")

            current_song_count = int(getattr(album, "songs_count", 0) or 0) + created_for_album
            should_hide = (
                hide_empty
                and current_song_count == 0
                and "-lastfm" in str(album.slug or "")
                and not album.spotify_id
                and not album.musicbrainz_id
                and not _has_album_interactions(album)
            )
            if should_hide:
                if dry_run:
                    self.stdout.write(f"[dry-run] hide empty placeholder {album.artist.name} - {album.title}")
                else:
                    album.is_approved = False
                    album.save(update_fields=["is_approved"])
                hidden_empty += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Last.fm placeholder repair {'dry-run' if dry_run else 'updated'}: "
                f"scanned={scanned} tracks_created={tracks_created} "
                f"hidden_empty={hidden_empty} failures={failures}"
            )
        )
