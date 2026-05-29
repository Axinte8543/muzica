from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from music.models import Album, Artist
from music.integrations import (
    CoverArtArchiveError,
    MusicExternalIntegrationService,
    SpotifyAPIError,
    SpotifyAuthError,
    safe_image_url,
)


@dataclass
class BackfillStats:
    scanned_artists: int = 0
    updated_artists: int = 0
    scanned_albums: int = 0
    updated_albums: int = 0


def _normalize(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _norm_key(value: str) -> str:
    # Lightweight normalization for matching Spotify artist credits.
    return "".join([c.lower() for c in _normalize(value) if c.isalnum()])


class Command(BaseCommand):
    help = "Backfill missing artist images and album covers (Spotify + Cover Art Archive)."

    def add_arguments(self, parser):
        parser.add_argument("--artists", action="store_true", help="Backfill Artist.image_url")
        parser.add_argument("--albums", action="store_true", help="Backfill Album.cover_url")
        parser.add_argument("--limit", type=int, default=0, help="Max records to process per section (0 = no limit)")
        parser.add_argument("--market", type=str, default="RO", help="Spotify market (default RO)")
        parser.add_argument("--dry-run", action="store_true", help="Compute changes without saving")

    def handle(self, *args, **options):
        do_artists = bool(options.get("artists"))
        do_albums = bool(options.get("albums"))
        if not do_artists and not do_albums:
            do_artists = True
            do_albums = True

        limit = max(0, int(options.get("limit") or 0))
        market = str(options.get("market") or "RO").strip() or "RO"
        dry_run = bool(options.get("dry_run"))

        stats = BackfillStats()

        integration = MusicExternalIntegrationService()
        spotify = None
        try:
            spotify = integration.spotify
        except SpotifyAuthError:
            spotify = None

        if do_artists:
            qs = Artist.objects.filter(image_url="").order_by("id")
            if limit:
                qs = qs[:limit]

            for artist in qs:
                stats.scanned_artists += 1
                if not spotify:
                    continue

                try:
                    if artist.spotify_id:
                        payload = spotify.get_artist(artist.spotify_id)
                        url = safe_image_url(payload)
                        if url and url != artist.image_url:
                            self.stdout.write(f"Artist image: {artist.name} <- Spotify")
                            if not dry_run:
                                artist.image_url = url
                                artist.save(update_fields=["image_url"])
                            stats.updated_artists += 1
                            continue

                    # Fallback to search if we have no spotify_id OR the stored
                    # spotify_id returns no images.
                    candidates = spotify.search_artist(name=artist.name, market=market, limit=3)
                    if not candidates:
                        continue
                    best = candidates[0]
                    url = safe_image_url(best)
                    if url:
                        self.stdout.write(f"Artist image: {artist.name} <- Spotify search")
                        if not dry_run:
                            cand_id = str(best.get("id") or "").strip()
                            cand_url = str((best.get("external_urls") or {}).get("spotify") or "").strip()
                            cand_pop = best.get("popularity")

                            artist.image_url = url
                            update_fields = ["image_url"]

                            if cand_id and not Artist.objects.filter(spotify_id=cand_id).exclude(pk=artist.pk).exists():
                                artist.spotify_id = cand_id
                                update_fields.append("spotify_id")
                            if cand_url:
                                artist.spotify_url = cand_url
                                update_fields.append("spotify_url")
                            if cand_pop is not None:
                                artist.popularity = cand_pop
                                update_fields.append("popularity")

                            artist.save(update_fields=update_fields)
                        stats.updated_artists += 1
                except SpotifyAPIError as e:
                    self.stdout.write(self.style.WARNING(f"Spotify artist error for {artist.name}: {e}"))

        if do_albums:
            qs = Album.objects.filter(cover_url="").select_related("artist").order_by("id")
            if limit:
                qs = qs[:limit]

            for album in qs:
                stats.scanned_albums += 1
                cover_url = ""
                cover_source = ""
                pending_spotify_id = ""
                pending_spotify_url = ""

                if spotify:
                    try:
                        if album.spotify_id:
                            payload = spotify.get_album(album.spotify_id, market=market)
                            cover_url = safe_image_url(payload)
                            if cover_url:
                                cover_source = "Spotify"
                        else:
                            candidates = spotify.search_album(
                                album_title=album.title,
                                artist_name=album.artist.name,
                                market=market,
                                limit=3,
                            )
                            if candidates:
                                best = candidates[0]
                                cover_url = safe_image_url(best)
                                if cover_url:
                                    cover_source = "Spotify"

                                cand_id = str(best.get("id") or "").strip()
                                cand_url = str((best.get("external_urls") or {}).get("spotify") or "").strip()
                                if cand_id and not Album.objects.filter(spotify_id=cand_id).exclude(pk=album.pk).exists():
                                    pending_spotify_id = cand_id
                                if cand_url:
                                    pending_spotify_url = cand_url

                            # Fallback: search by album title only, then pick a result
                            # that matches our artist (Spotify credits can differ).
                            if not cover_url:
                                q = f"album:{album.title}".strip()
                                data = spotify.search(q=q, types=["album"], market=market, limit=5)
                                items = ((data.get("albums") or {}).get("items")) or []
                                if isinstance(items, list) and items:
                                    target_artist_key = _norm_key(album.artist.name)
                                    for it in items:
                                        if not isinstance(it, dict):
                                            continue
                                        it_artists = it.get("artists") or []
                                        if not isinstance(it_artists, list):
                                            continue
                                        if not any(_norm_key((a or {}).get("name") or "") == target_artist_key for a in it_artists if isinstance(a, dict)):
                                            continue

                                        cover_url = _safe_first_image_url(it.get("images"))
                                        if cover_url:
                                            cover_source = "Spotify"

                                        cand_id = str(it.get("id") or "").strip()
                                        cand_url = str((it.get("external_urls") or {}).get("spotify") or "").strip()
                                        if cand_id and not Album.objects.filter(spotify_id=cand_id).exclude(pk=album.pk).exists():
                                            pending_spotify_id = pending_spotify_id or cand_id
                                        if cand_url:
                                            pending_spotify_url = pending_spotify_url or cand_url
                                        break
                    except SpotifyAPIError as e:
                        self.stdout.write(self.style.WARNING(f"Spotify album error for {album.title}: {e}"))

                if not cover_url and album.musicbrainz_id:
                    try:
                        cover_url = integration.cover_art_archive.get_release_group_cover_url(
                            release_group_mbid=album.musicbrainz_id,
                        )
                        if cover_url:
                            cover_source = "CAA"
                    except CoverArtArchiveError as e:
                        self.stdout.write(self.style.WARNING(f"CAA error for {album.title}: {e}"))

                if cover_url and cover_url != album.cover_url:
                    self.stdout.write(f"Album cover: {album.artist.name} - {album.title} <- {cover_source or 'unknown'}")
                    if not dry_run:
                        album.cover_url = cover_url
                        update_fields = ["cover_url"]

                        if pending_spotify_id and not album.spotify_id:
                            album.spotify_id = pending_spotify_id
                            update_fields.append("spotify_id")
                        if pending_spotify_url and (pending_spotify_url != album.spotify_url):
                            album.spotify_url = pending_spotify_url
                            update_fields.append("spotify_url")

                        try:
                            album.save(update_fields=update_fields)
                        except IntegrityError as e:
                            self.stdout.write(self.style.WARNING(f"DB integrity error for album {album.id} ({album.title}): {e}"))
                            continue
                    stats.updated_albums += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Done. "
                f"artists_scanned={stats.scanned_artists} artists_updated={stats.updated_artists} "
                f"albums_scanned={stats.scanned_albums} albums_updated={stats.updated_albums} "
                f"dry_run={dry_run} spotify={'yes' if spotify else 'no'}"
            )
        )
