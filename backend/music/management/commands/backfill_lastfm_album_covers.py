from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from music.lastfm import LastFMAPIError, LastFMClient
from music.models import Album


def _image_url(payload: dict[str, Any]) -> str:
    images = payload.get("image")
    if not isinstance(images, list):
        return ""
    for item in reversed(images):
        if not isinstance(item, dict):
            continue
        url = str(item.get("#text") or "").strip()
        if url:
            return url
    return ""


class Command(BaseCommand):
    help = "Backfill missing album covers from Last.fm album.getinfo."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        limit = max(0, int(options.get("limit") or 0))
        dry_run = bool(options.get("dry_run"))

        qs = Album.objects.filter(cover_url="", is_approved=True, artist__is_approved=True).select_related("artist").order_by("id")
        if limit:
            qs = qs[:limit]

        client = LastFMClient()
        scanned = 0
        updated = 0
        failures = 0

        for album in qs:
            scanned += 1
            try:
                payload = client.get_album_info(artist_name=album.artist.name, album_title=album.title)
            except LastFMAPIError:
                failures += 1
                continue

            url = _image_url(payload)
            if not url:
                continue

            self.stdout.write(f"Album cover: {album.artist.name} - {album.title} <- Last.fm")
            if not dry_run:
                album.cover_url = url
                album.save(update_fields=["cover_url"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Last.fm album cover backfill {'dry-run' if dry_run else 'updated'}: "
                f"scanned={scanned} updated={updated} failures={failures}"
            )
        )
