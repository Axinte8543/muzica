from __future__ import annotations

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db import transaction
from django.utils.text import slugify

from music.lastfm import LastFMAPIError, LastFMClient
from music.models import Album, Artist, Song


PLACEHOLDER_RELEASE_DATE = date(1970, 1, 1)


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _unique_slug(model, base: str) -> str:
    base_slug = slugify(_normalize_text(base))
    if not base_slug:
        base_slug = "item"

    slug = base_slug
    suffix = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def _lastfm_image_url(payload: dict[str, Any]) -> str:
    images = payload.get("image")
    if not isinstance(images, list):
        return ""

    for item in reversed(images):
        if not isinstance(item, dict):
            continue
        url = _normalize_text(item.get("#text") or "")
        if url:
            return url
    return ""


def _artist_matches(payload: dict[str, Any], artist: Artist) -> bool:
    raw = payload.get("artist")
    if isinstance(raw, dict):
        name = _normalize_text(raw.get("name") or "")
    else:
        name = _normalize_text(raw or "")
    if not name:
        return True
    return name.lower() == artist.name.lower()


class Command(BaseCommand):
    help = "Import missing top albums and top tracks from Last.fm for existing approved artists."

    def add_arguments(self, parser):
        parser.add_argument("--artists", type=str, default="", help="Comma-separated artist names")
        parser.add_argument("--all-existing", action="store_true", help="Process all approved local artists")
        parser.add_argument("--artist-limit", type=int, default=0, help="Limit number of artists processed")
        parser.add_argument("--album-limit", type=int, default=10, help="Last.fm top albums per artist")
        parser.add_argument("--track-limit", type=int, default=20, help="Last.fm top tracks per artist")
        parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")
        parser.add_argument("--approved", action="store_true", help="Mark imported records as approved")
        parser.add_argument("--romanian-only", action="store_true", help="Only process artists marked Romanian")
        parser.add_argument(
            "--include-ambiguous",
            action="store_true",
            help="Also process very short names, unusual names, and duplicate artist names",
        )

    def handle(self, *args, **options):
        names_raw = _normalize_text(options.get("artists") or "")
        all_existing = bool(options.get("all_existing"))
        artist_limit = max(0, int(options.get("artist_limit") or 0))
        album_limit = max(0, int(options.get("album_limit") or 10))
        track_limit = max(0, int(options.get("track_limit") or 20))
        dry_run = bool(options.get("dry_run"))
        approved = bool(options.get("approved"))
        romanian_only = bool(options.get("romanian_only"))
        include_ambiguous = bool(options.get("include_ambiguous"))

        if names_raw:
            names = [_normalize_text(name) for name in names_raw.split(",") if _normalize_text(name)]
            qs = Artist.objects.filter(name__in=names, is_approved=True)
        elif all_existing:
            qs = Artist.objects.filter(is_approved=True)
        else:
            self.stderr.write("Provide --artists or --all-existing")
            return

        if romanian_only:
            qs = qs.filter(is_romanian=True)

        artists = list(qs.order_by("name", "id"))

        if not include_ambiguous:
            name_counts = {
                row["name_lower"]: row["count"]
                for row in (
                    Artist.objects.filter(is_approved=True)
                    .extra(select={"name_lower": "LOWER(name)"})
                    .values("name_lower")
                    .annotate(count=Count("id"))
                )
            }
            filtered_artists: list[Artist] = []
            skipped_ambiguous = 0
            for artist in artists:
                name = _normalize_text(artist.name)
                if len(slugify(name)) <= 4 and not artist.musicbrainz_id:
                    skipped_ambiguous += 1
                    continue
                if "more than one artist with this name" in (artist.bio or "").lower():
                    skipped_ambiguous += 1
                    continue
                if len(slugify(name)) <= 2 or name.startswith("¿"):
                    skipped_ambiguous += 1
                    continue
                if name_counts.get(name.lower(), 0) > 1:
                    skipped_ambiguous += 1
                    continue
                filtered_artists.append(artist)
            artists = filtered_artists
        else:
            skipped_ambiguous = 0

        if artist_limit:
            artists = artists[:artist_limit]

        client = LastFMClient()
        processed = 0
        failures = 0
        albums_created = 0
        songs_created = 0
        skipped_wrong_artist = 0

        self.stdout.write(f"Artists to process: {len(artists)} (skipped_ambiguous={skipped_ambiguous})")

        for artist in artists:
            processed += 1
            try:
                album_items = client.get_top_albums(
                    artist_name=artist.name,
                    artist_mbid=artist.musicbrainz_id or "",
                    limit=album_limit,
                ) if album_limit else []
                track_items = client.get_top_tracks(
                    artist_name=artist.name,
                    artist_mbid=artist.musicbrainz_id or "",
                    limit=track_limit,
                ) if track_limit else []
            except LastFMAPIError as exc:
                failures += 1
                self.stdout.write(self.style.WARNING(f"Last.fm failed for {artist.name}: {exc}"))
                continue

            new_albums: list[tuple[str, str]] = []
            for item in album_items:
                if not _artist_matches(item, artist):
                    skipped_wrong_artist += 1
                    continue
                title = _normalize_text(item.get("name") or "")
                if not title:
                    continue
                if Album.objects.filter(artist=artist, title__iexact=title).exists():
                    continue
                cover_url = _lastfm_image_url(item)
                new_albums.append((title, cover_url))

            new_tracks: list[str] = []
            for item in track_items:
                if not _artist_matches(item, artist):
                    skipped_wrong_artist += 1
                    continue
                title = _normalize_text(item.get("name") or "")
                if not title:
                    continue
                if Song.objects.filter(artist=artist, title__iexact=title).exists():
                    continue
                new_tracks.append(title)

            if not new_albums and not new_tracks:
                continue

            if dry_run:
                self.stdout.write(
                    f"[dry-run] {artist.name}: albums={len(new_albums)} tracks={len(new_tracks)}"
                )
                albums_created += len(new_albums)
                songs_created += len(new_tracks)
                continue

            with transaction.atomic():
                for title, cover_url in new_albums:
                    Album.objects.create(
                        artist=artist,
                        title=title,
                        slug=_unique_slug(Album, f"{artist.name}-{title}-lastfm"),
                        cover_url=cover_url,
                        release_date=PLACEHOLDER_RELEASE_DATE,
                        mb_primary_type="album",
                        is_approved=approved,
                    )
                    albums_created += 1

                for title in new_tracks:
                    Song.objects.create(
                        artist=artist,
                        album=None,
                        title=title,
                        slug=_unique_slug(Song, f"{artist.name}-{title}-lastfm"),
                        duration_seconds=0,
                        is_approved=approved,
                    )
                    songs_created += 1

            self.stdout.write(f"{artist.name}: added albums={len(new_albums)} tracks={len(new_tracks)}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Last.fm catalog import {'dry-run' if dry_run else 'updated'}: "
                f"processed={processed} failures={failures} "
                f"albums_created={albums_created} songs_created={songs_created} "
                f"skipped_wrong_artist={skipped_wrong_artist}"
            )
        )
