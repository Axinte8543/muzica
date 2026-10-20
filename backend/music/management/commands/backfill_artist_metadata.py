from __future__ import annotations

import html
import json
import re
from urllib.parse import unquote, urlparse
from urllib import parse, request
from urllib.error import HTTPError, URLError
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from music.lastfm import LastFMAPIError, LastFMClient
from music.models import Artist, Genre
from music.musicbrainz import MusicBrainzAPIError, MusicBrainzClient
from music.spotify import SpotifyAPIError, SpotifyAuthError, SpotifyClient, SpotifyRateLimitError


_G_GENERIC_GENRE_NAMES = {
    "unknown",
    "miscellaneous",
    "seen live",
    "favorites",
    "favorite",
}


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _clean_paragraph(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s*Read more on Last\.fm.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_wikipedia_title(payload: dict[str, Any]) -> str:
    relations = payload.get("relations") or []
    if not isinstance(relations, list):
        return ""

    for rel in relations:
        if not isinstance(rel, dict):
            continue
        url_obj = rel.get("url")
        if not isinstance(url_obj, dict):
            continue
        resource = _normalize_text(url_obj.get("resource") or "")
        if "wikipedia.org/wiki/" not in resource:
            continue
        parsed = urlparse(resource)
        title = parsed.path.rsplit("/", 1)[-1].strip()
        if title:
            return unquote(title)
    return ""


def _fetch_wikipedia_summary(title: str) -> str:
    clean = _normalize_text(title)
    if not clean:
        return ""

    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean.replace(' ', '_')}"
    req = request.Request(url, headers={"User-Agent": "licenta-muzica"}, method="GET")
    try:
        with request.urlopen(req, timeout=30) as res:
            status = int(getattr(res, "status", 200))
            body = res.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError):
        return ""

    if status != 200:
        return ""

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return ""
    if not isinstance(data, dict):
        return ""

    extract = _normalize_text(data.get("extract") or "")
    if extract:
        return _clean_paragraph(extract)

    desc = _normalize_text(data.get("description") or "")
    return _clean_paragraph(desc)


def _slug_key(value: str) -> str:
    return slugify(_normalize_text(value))


def _unique_genre(name: str) -> Genre:
    clean = _normalize_text(name)
    slug = _slug_key(clean)
    if not slug:
        raise ValueError("Empty genre")
    genre, _ = Genre.objects.get_or_create(slug=slug, defaults={"name": clean})
    if genre.name != clean:
        genre.name = clean
        genre.save(update_fields=["name"])
    return genre


def _extract_musicbrainz_genres(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("genres") or []
    if isinstance(raw, dict):
        raw = [raw]

    scored: list[tuple[int, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = _normalize_text(item.get("name") or "")
        if not name:
            continue
        try:
            count = int(item.get("count") or 0)
        except Exception:
            count = 0
        scored.append((count, name))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [name for _, name in scored]


def _extract_lastfm_genres(payload: dict[str, Any]) -> list[str]:
    tags = (((payload.get("tags") or {}).get("tag")) or [])
    if isinstance(tags, dict):
        tags = [tags]

    scored: list[tuple[int, str]] = []
    for item in tags:
        if not isinstance(item, dict):
            continue
        name = _normalize_text(item.get("name") or "")
        if not name:
            continue
        if name.lower() in _G_GENERIC_GENRE_NAMES:
            continue
        try:
            count = int(item.get("count") or 0)
        except Exception:
            count = 0
        scored.append((count, name))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [name for _, name in scored]


def _extract_spotify_genres(payload: dict[str, Any]) -> list[str]:
    genres = payload.get("genres") or []
    if not isinstance(genres, list):
        return []
    result: list[str] = []
    for item in genres:
        name = _normalize_text(item)
        if name:
            result.append(name)
    return result


def _merge_genres(*sources: list[str], limit: int = 6) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for source in sources:
        for name in source:
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)
            merged.append(name)
            if len(merged) >= limit:
                return merged
    return merged


class Command(BaseCommand):
    help = "Backfill artist metadata from MusicBrainz, Spotify, and Last.fm."

    def add_arguments(self, parser):
        parser.add_argument(
            "--artists",
            type=str,
            default="",
            help="Comma-separated list of artist names to enrich",
        )
        parser.add_argument(
            "--artists-file",
            type=str,
            default="",
            help="Path to a text file with one artist name per line",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit how many artists are processed",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without saving",
        )
        parser.add_argument(
            "--replace-genres",
            action="store_true",
            help="Replace existing artist genres with inferred ones",
        )
        parser.add_argument(
            "--replace-bio",
            action="store_true",
            help="Replace an existing bio if a better source is found",
        )
        parser.add_argument(
            "--skip-spotify",
            action="store_true",
            help="Skip Spotify lookups",
        )
        parser.add_argument(
            "--skip-lastfm",
            action="store_true",
            help="Skip Last.fm lookups",
        )
        parser.add_argument(
            "--missing-only",
            action="store_true",
            help="Only process artists missing bio or all artist genres",
        )

    def handle(self, *args, **options):
        names_raw = str(options.get("artists") or "").strip()
        artists_file = str(options.get("artists_file") or "").strip()
        limit = max(0, int(options.get("limit") or 0))
        dry_run = bool(options.get("dry_run"))
        replace_genres = bool(options.get("replace_genres"))
        replace_bio = bool(options.get("replace_bio"))
        skip_spotify = bool(options.get("skip_spotify"))
        skip_lastfm = bool(options.get("skip_lastfm"))
        missing_only = bool(options.get("missing_only"))

        target_names: list[str] = []
        if names_raw:
            target_names.extend([_normalize_text(name) for name in names_raw.split(",") if _normalize_text(name)])
        if artists_file:
            with open(artists_file, "r", encoding="utf-8") as handle:
                for line in handle:
                    name = _normalize_text(line)
                    if name and not name.startswith("#"):
                        target_names.append(name)

        if target_names:
            seen: set[str] = set()
            resolved: list[Artist] = []
            for name in target_names:
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                matches = list(Artist.objects.filter(name__iexact=name).order_by("id"))
                if not matches:
                    self.stdout.write(self.style.WARNING(f"Artist not found in DB: {name}"))
                    continue
                resolved.extend(matches)
            artists = resolved
        else:
            artists = list(Artist.objects.order_by("id"))

        if missing_only:
            filtered: list[Artist] = []
            for artist in artists:
                if not _normalize_text(artist.bio) or not artist.genres.exists():
                    filtered.append(artist)
            artists = filtered

        if limit:
            artists = artists[:limit]

        mb = MusicBrainzClient()
        spotify: SpotifyClient | None = None
        if not skip_spotify:
            try:
                spotify = SpotifyClient()
            except SpotifyAuthError as exc:
                self.stdout.write(self.style.WARNING(f"Spotify disabled: {exc}"))

        lastfm: LastFMClient | None = None
        if not skip_lastfm:
            try:
                lastfm = LastFMClient()
            except LastFMAPIError as exc:
                self.stdout.write(self.style.WARNING(f"Last.fm disabled: {exc}"))

        summary = {
            "artists": 0,
            "bios": 0,
            "genres": 0,
        }
        lastfm_failures = 0
        spotify_failures = 0
        spotify_rate_limited = False

        for artist in artists:
            mb_payload: dict[str, Any] = {}
            spotify_payload: dict[str, Any] = {}
            lastfm_payload: dict[str, Any] = {}
            changed_fields: list[str] = []

            try:
                if artist.musicbrainz_id:
                    mb_payload = mb.get_artist(artist_mbid=artist.musicbrainz_id, inc="annotation+genres+aliases+url-rels")
                else:
                    search = mb.search_artist(name=artist.name, query=f'artist:"{artist.name}"', limit=5)
                    matches = search.get("artists") or []
                    if isinstance(matches, list) and matches:
                        best = next((item for item in matches if isinstance(item, dict) and _normalize_text(item.get("name") or "").lower() == artist.name.lower()), None)
                        if best is None and isinstance(matches[0], dict):
                            best = matches[0]
                        if isinstance(best, dict):
                            mbid = _normalize_text(best.get("id") or "")
                            if mbid:
                                mb_payload = mb.get_artist(artist_mbid=mbid, inc="annotation+genres+aliases+url-rels")
            except MusicBrainzAPIError as exc:
                self.stdout.write(self.style.WARNING(f"MusicBrainz failed for {artist.name}: {exc}"))

            if spotify is not None:
                try:
                    if artist.spotify_id:
                        spotify_payload = spotify.get_artist(artist.spotify_id)
                    else:
                        candidates = spotify.search_artist(name=artist.name, market="RO", limit=5)
                        if candidates:
                            best = next((item for item in candidates if _normalize_text(item.get("name") or "").lower() == artist.name.lower()), candidates[0])
                            if isinstance(best, dict):
                                spotify_payload = best
                                spotify_id = _normalize_text(best.get("id") or "")
                except SpotifyRateLimitError as exc:
                    spotify_failures += 1
                    spotify_rate_limited = True
                    spotify = None
                except SpotifyAPIError as exc:
                    spotify_failures += 1

            if lastfm is not None:
                try:
                    lastfm_payload = lastfm.get_artist_info(
                        artist_name=artist.name,
                        artist_mbid=artist.musicbrainz_id or _normalize_text(mb_payload.get("id") or ""),
                    )
                except LastFMAPIError as exc:
                    lastfm_failures += 1

            bio_candidates: list[str] = []
            wiki_title = _extract_wikipedia_title(mb_payload)
            if wiki_title:
                wiki_summary = _fetch_wikipedia_summary(wiki_title)
                if wiki_summary:
                    bio_candidates.append(wiki_summary)

            mb_annotation = _clean_paragraph(_normalize_text(mb_payload.get("annotation") or ""))
            if mb_annotation:
                bio_candidates.append(mb_annotation)

            lastfm_bio = _clean_paragraph(_normalize_text((((lastfm_payload.get("bio") or {}).get("summary")) or "")))
            if lastfm_bio:
                bio_candidates.append(lastfm_bio)

            if bio_candidates:
                candidate = bio_candidates[0]
                if (not artist.bio) or replace_bio:
                    if artist.bio != candidate:
                        artist.bio = candidate
                        changed_fields.append("bio")
                        summary["bios"] += 1

            mb_genres = _extract_musicbrainz_genres(mb_payload)
            spotify_genres = _extract_spotify_genres(spotify_payload) if spotify_payload else []
            lastfm_genres = _extract_lastfm_genres(lastfm_payload) if lastfm_payload else []
            genre_names = _merge_genres(mb_genres, spotify_genres, lastfm_genres, limit=6)

            if genre_names:
                existing_slugs = set(artist.genres.values_list("slug", flat=True))
                genre_slugs = {_slug_key(name) for name in genre_names if _slug_key(name)}
                if replace_genres:
                    if existing_slugs != genre_slugs:
                        changed_fields.append("genres")
                        summary["genres"] += 1
                else:
                    missing_names = [
                        name for name in genre_names
                        if _slug_key(name) and _slug_key(name) not in existing_slugs
                    ]
                    if missing_names:
                        changed_fields.append("genres")
                        summary["genres"] += 1

            if not changed_fields:
                continue

            summary["artists"] += 1
            if dry_run:
                self.stdout.write(f"[dry-run] {artist.name}: {', '.join(changed_fields)}")
                continue

            with transaction.atomic():
                artist.save()
                if genre_names and ("genres" in changed_fields):
                    genre_objs = [_unique_genre(name) for name in genre_names]
                    if replace_genres:
                        artist.genres.set(genre_objs)
                    else:
                        existing_ids = set(artist.genres.values_list("id", flat=True))
                        missing = [genre for genre in genre_objs if genre.id not in existing_ids]
                        if missing:
                            artist.genres.add(*missing)

        mode = "dry-run" if dry_run else "updated"
        if lastfm_failures:
            self.stdout.write(
                self.style.WARNING(
                    f"Last.fm lookups failed for {lastfm_failures} artist(s); continuing with MusicBrainz and Spotify data"
                )
            )
        if spotify_failures:
            message = f"Spotify lookups failed for {spotify_failures} artist(s)"
            if spotify_rate_limited:
                message += "; Spotify was disabled for the rest of the run after a rate limit"
            self.stdout.write(self.style.WARNING(message))
        self.stdout.write(
            self.style.SUCCESS(
                f"Artist metadata backfill {mode}: artists={summary['artists']} bios={summary['bios']} genres={summary['genres']}"
            )
        )
