from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from music.models import Album
from music.musicbrainz import MusicBrainzAPIError, MusicBrainzClient


PLACEHOLDER_DATE = date(1970, 1, 1)


def _parse_date(raw: str) -> date | None:
    raw = str(raw or "").strip()
    if not raw:
        return None
    try:
        parts = raw.split("-")
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        if len(parts) == 2:
            return date(int(parts[0]), int(parts[1]), 1)
        if len(parts) == 1:
            return date(int(parts[0]), 1, 1)
    except (TypeError, ValueError):
        return None
    return None


class Command(BaseCommand):
    help = "Repair album release dates that still use the 1970 placeholder."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--limit", type=int, default=0)

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        limit = max(0, int(options.get("limit") or 0))
        updated_from_duplicate = 0
        updated_from_musicbrainz = 0
        failures = 0

        qs = Album.objects.filter(release_date=PLACEHOLDER_DATE).select_related("artist").order_by("id")
        if limit:
            qs = qs[:limit]

        mb = MusicBrainzClient()

        with transaction.atomic():
            for album in qs:
                better = (
                    Album.objects.filter(artist=album.artist, title__iexact=album.title)
                    .exclude(id=album.id)
                    .exclude(release_date=PLACEHOLDER_DATE)
                    .order_by("release_date")
                    .first()
                )
                if better is not None:
                    if dry_run:
                        self.stdout.write(
                            f"[dry-run] duplicate date {album.artist.name} - {album.title}: {album.release_date} -> {better.release_date}"
                        )
                    else:
                        album.release_date = better.release_date
                        album.save(update_fields=["release_date"])
                    updated_from_duplicate += 1
                    continue

                if not album.musicbrainz_id:
                    continue

                try:
                    payload = mb.get_release_group(release_group_mbid=album.musicbrainz_id)
                except MusicBrainzAPIError as exc:
                    failures += 1
                    self.stdout.write(self.style.WARNING(f"MusicBrainz failed for {album.title}: {exc}"))
                    continue

                parsed = _parse_date(payload.get("first-release-date") or "")
                if parsed is None or parsed == PLACEHOLDER_DATE:
                    continue

                if dry_run:
                    self.stdout.write(
                        f"[dry-run] musicbrainz date {album.artist.name} - {album.title}: {album.release_date} -> {parsed}"
                    )
                else:
                    album.release_date = parsed
                    album.save(update_fields=["release_date"])
                updated_from_musicbrainz += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Album date repair {'dry-run' if dry_run else 'updated'}: "
                f"duplicate={updated_from_duplicate} musicbrainz={updated_from_musicbrainz} failures={failures}"
            )
        )
