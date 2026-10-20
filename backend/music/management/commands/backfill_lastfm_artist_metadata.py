from __future__ import annotations

import html
import re
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from django.utils.text import slugify

from music.lastfm import LastFMAPIError, LastFMClient
from music.models import Artist, Genre


_GENERIC_TAGS = {
    "awesome",
    "brasov",
    "connect-r",
    "creative commons",
    "dj",
    "dj's",
    "ex-aria",
    "seen live",
    "female voice",
    "female vocalist",
    "favorites",
    "favorite",
    "fucking awesome",
    "spotify",
    "last.fm",
    "lastfm",
    "liebeslied",
    "my favorite",
    "pe sistem",
    "romania",
    "romanian",
}


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _clean_lastfm_bio(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s*Read more on Last\.fm.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_lastfm_genres(payload: dict[str, Any], *, artist_name: str, limit: int) -> list[str]:
    tags = (((payload.get("tags") or {}).get("tag")) or [])
    if isinstance(tags, dict):
        tags = [tags]
    if not isinstance(tags, list):
        return []

    scored: list[tuple[int, str]] = []
    seen: set[str] = set()
    for item in tags:
        if not isinstance(item, dict):
            continue
        name = _normalize_text(item.get("name") or "")
        if not name:
            continue
        key = name.lower()
        if key in seen or key in _GENERIC_TAGS or key == _normalize_text(artist_name).lower():
            continue
        if any(bad_word in key for bad_word in ("fuck", "shit")):
            continue
        seen.add(key)
        try:
            count = int(item.get("count") or 0)
        except (TypeError, ValueError):
            count = 0
        scored.append((count, name))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [name for _, name in scored[:limit]]


def _get_or_create_genre(name: str) -> Genre | None:
    clean = _normalize_text(name)
    slug = slugify(clean)
    if not slug:
        return None

    genre, created = Genre.objects.get_or_create(slug=slug, defaults={"name": clean})
    if not created and genre.name != clean:
        genre.name = clean
        genre.save(update_fields=["name"])
    return genre


class Command(BaseCommand):
    help = "Fill missing artist bio and empty artist genres from Last.fm."

    def add_arguments(self, parser):
        parser.add_argument(
            "--artists",
            type=str,
            default="",
            help="Comma-separated artist names to process. Defaults to all missing metadata.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit how many artists are processed.",
        )
        parser.add_argument(
            "--genre-limit",
            type=int,
            default=6,
            help="Maximum Last.fm tags to add as genres per artist.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show changes without saving.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        limit = max(0, int(options.get("limit") or 0))
        genre_limit = max(1, int(options.get("genre_limit") or 6))
        names_raw = _normalize_text(options.get("artists") or "")

        if names_raw:
            names = [_normalize_text(name) for name in names_raw.split(",") if _normalize_text(name)]
            artists = list(
                Artist.objects.annotate(genres_count=Count("genres"))
                .filter(name__in=names)
                .order_by("id")
            )
            found_names = {artist.name.lower() for artist in artists}
            for name in names:
                if name.lower() not in found_names:
                    self.stdout.write(self.style.WARNING(f"Artist not found: {name}"))
        else:
            artists = list(
                Artist.objects.annotate(genres_count=Count("genres"))
                .filter(Q(bio__isnull=True) | Q(bio="") | Q(genres_count=0))
                .order_by("id")
            )

        if limit:
            artists = artists[:limit]

        client = LastFMClient()
        processed = 0
        updated_artists = 0
        updated_bios = 0
        updated_genres = 0
        failures = 0

        self.stdout.write(f"Artists to process: {len(artists)}")

        for artist in artists:
            needs_bio = not _normalize_text(artist.bio)
            needs_genres = int(getattr(artist, "genres_count", 0) or 0) == 0
            if not needs_bio and not needs_genres:
                continue

            processed += 1
            try:
                payload = client.get_artist_info(
                    artist_name=artist.name,
                    artist_mbid=artist.musicbrainz_id or "",
                )
            except LastFMAPIError as exc:
                failures += 1
                self.stdout.write(self.style.WARNING(f"Last.fm failed for {artist.name}: {exc}"))
                continue

            bio = _clean_lastfm_bio((((payload.get("bio") or {}).get("summary")) or ""))
            genre_names = _extract_lastfm_genres(
                payload,
                artist_name=artist.name,
                limit=genre_limit,
            )

            next_bio = bio if needs_bio and bio else ""
            next_genres = genre_names if needs_genres else []
            if not next_bio and not next_genres:
                continue

            changes: list[str] = []
            if next_bio:
                changes.append(f"bio len={len(next_bio)}")
            if next_genres:
                changes.append("genres=" + ", ".join(next_genres))

            if dry_run:
                self.stdout.write(f"[dry-run] {artist.name}: {'; '.join(changes)}")
                updated_artists += 1
                updated_bios += 1 if next_bio else 0
                updated_genres += 1 if next_genres else 0
                continue

            with transaction.atomic():
                save_fields: list[str] = []
                if next_bio:
                    artist.bio = next_bio
                    save_fields.append("bio")
                if save_fields:
                    artist.save(update_fields=save_fields)
                if next_genres:
                    genres = [genre for genre in (_get_or_create_genre(name) for name in next_genres) if genre]
                    if genres:
                        artist.genres.add(*genres)

            updated_artists += 1
            updated_bios += 1 if next_bio else 0
            updated_genres += 1 if next_genres else 0
            self.stdout.write(f"{artist.name}: {', '.join(changes)}")

        mode = "dry-run" if dry_run else "updated"
        if failures:
            self.stdout.write(self.style.WARNING(f"Last.fm failures: {failures}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Last.fm artist metadata {mode}: processed={processed} artists={updated_artists} bios={updated_bios} genres={updated_genres}"
            )
        )
