from __future__ import annotations

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from music.models import Album, Artist, Song
from music.musicbrainz import MusicBrainzClient, MusicBrainzAPIError


def _unique_slug(model, base: str) -> str:
    base_slug = slugify(str(base or "").strip())
    if not base_slug:
        base_slug = "item"

    slug = base_slug
    suffix = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def _parse_date_best_effort(raw: str | None) -> date:
    raw = (raw or "").strip()
    if not raw:
        return date(1970, 1, 1)

    try:
        parts = raw.split("-")
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        if len(parts) == 2:
            return date(int(parts[0]), int(parts[1]), 1)
        if len(parts) == 1:
            return date(int(parts[0]), 1, 1)
    except Exception:
        return date(1970, 1, 1)

    return date(1970, 1, 1)


def _artist_area_is_romania(artist: dict[str, Any]) -> bool:
                                         
    area = artist.get("area") or {}
    name = str(area.get("name") or "").strip().lower()
    return name == "romania"


class Command(BaseCommand):
    help = "Import an artist discography from MusicBrainz (artist -> release-groups -> releases -> tracklist)."

    def add_arguments(self, parser):
        parser.add_argument("name", type=str, help="Artist name to search (e.g., Puya)")
        parser.add_argument(
            "--mbid",
            type=str,
            default="",
            help="Optional: import directly by MusicBrainz Artist MBID (skips search)",
        )
        parser.add_argument(
            "--romanian-only",
            action="store_true",
            help="During search, prefer artists with area:Romania and mark is_romanian=true",
        )
        parser.add_argument(
            "--force-romanian",
            action="store_true",
            help="Mark artist is_romanian=true regardless of MusicBrainz area",
        )
        parser.add_argument(
            "--max-release-groups",
            type=int,
            default=25,
            help="Max release-groups to import (default 25)",
        )
        parser.add_argument(
            "--max-releases-per-group",
            type=int,
            default=5,
            help="How many releases to inspect per release-group to find a tracklist (default 5)",
        )
        parser.add_argument(
            "--approved",
            action="store_true",
            help="Mark imported artist/albums/songs as approved",
        )

    def handle(self, *args, **options):
        name: str = str(options["name"] or "").strip()
        mbid: str = str(options["mbid"] or "").strip()
        romanian_only: bool = bool(options["romanian_only"])
        force_romanian: bool = bool(options["force_romanian"])
        max_rgs: int = max(1, int(options["max_release_groups"] or 25))
        max_releases_per_group: int = max(1, int(options["max_releases_per_group"] or 5))
        approved: bool = bool(options["approved"])

        if not name and not mbid:
            raise CommandError("Provide --mbid or a name")

        mb = MusicBrainzClient()

        artist_obj: dict[str, Any] | None = None
        if mbid:
            try:
                artist_obj = mb.get_artist(artist_mbid=mbid)
            except MusicBrainzAPIError as e:
                                                                           
                try:
                    payload = mb.search_artist(name=name, query=f"arid:{mbid}", limit=5)
                except MusicBrainzAPIError as e2:
                    raise CommandError(str(e2))
                artist_list = payload.get("artists") or []
                artist_obj = next((a for a in artist_list if str(a.get("id") or "").strip() == mbid), None)
        else:
            query = f"artist:{name}"
            if romanian_only:
                query = f"artist:{name} AND area:Romania"

            try:
                payload = mb.search_artist(name=name, query=query, limit=10)
            except MusicBrainzAPIError as e:
                raise CommandError(str(e))

            artist_list = payload.get("artists") or []
            if not artist_list:
                raise CommandError("No artists found on MusicBrainz")

                                                                       
            def score(a: dict[str, Any]) -> tuple[int, int, int]:
                n = str(a.get("name") or "").strip().lower()
                exact = 1 if n == name.lower() else 0
                ro = 1 if _artist_area_is_romania(a) else 0
                                                          
                return (exact, ro, int(a.get("score") or 0))

            artist_list.sort(key=score, reverse=True)
            artist_obj = artist_list[0]

        if not artist_obj:
            raise CommandError("Could not resolve artist")

        artist_mbid = str(artist_obj.get("id") or "").strip()
        artist_name = str(artist_obj.get("name") or "").strip() or name
        if not artist_mbid:
            raise CommandError("MusicBrainz artist missing id")

        is_romanian = True

        with transaction.atomic():
            db_artist = Artist.objects.filter(musicbrainz_id=artist_mbid).first()
            created = False

            if db_artist is None:
                                                                                       
                                                                               
                candidate = Artist.objects.filter(name__iexact=artist_name).first()
                if candidate is not None and (not candidate.musicbrainz_id or candidate.musicbrainz_id == artist_mbid):
                    db_artist = candidate
                else:
                    db_artist = Artist(
                        musicbrainz_id=artist_mbid,
                        name=artist_name,
                        slug=_unique_slug(Artist, artist_name),
                        is_romanian=is_romanian,
                        is_approved=approved,
                    )
                    db_artist.save()
                    created = True

            dirty = False
            if not db_artist.musicbrainz_id:
                db_artist.musicbrainz_id = artist_mbid
                dirty = True
            if artist_name and db_artist.name != artist_name:
                db_artist.name = artist_name
                dirty = True
            if not db_artist.is_romanian:
                db_artist.is_romanian = True
                dirty = True
            if approved and not db_artist.is_approved:
                db_artist.is_approved = True
                dirty = True
            if dirty:
                db_artist.save()

                                   
        rg_offset = 0
        rg_limit = 100
        release_groups: list[dict[str, Any]] = []
        while len(release_groups) < max_rgs:
            try:
                rg_payload = mb.artist_release_groups(artist_mbid=artist_mbid, limit=rg_limit, offset=rg_offset)
            except MusicBrainzAPIError as e:
                raise CommandError(str(e))

            rgs = rg_payload.get("release-groups") or []
            if not rgs:
                break
            for rg in rgs:
                release_groups.append(rg)
                if len(release_groups) >= max_rgs:
                    break

            rg_offset += len(rgs)
            total = rg_payload.get("release-group-count")
            if total is not None and rg_offset >= int(total):
                break

        imported_albums = 0
        imported_songs = 0

        for rg in release_groups:
            rg_id = str(rg.get("id") or "").strip()
            if not rg_id:
                continue

            title = str(rg.get("title") or "").strip() or "Unknown Album"
            first_release_date = _parse_date_best_effort(rg.get("first-release-date"))
            primary_type = str(rg.get("primary-type") or "").strip().lower()
            secondary_types = rg.get("secondary-types") or []
            if not isinstance(secondary_types, list):
                secondary_types = []
            secondary_types_norm = [str(x).strip().lower() for x in secondary_types if str(x).strip()]
            secondary_types_csv = ",".join(secondary_types_norm)
            if primary_type and primary_type not in {"album", "single", "ep"}:
                                                                 
                pass

            with transaction.atomic():
                album_obj, created = Album.objects.get_or_create(
                    musicbrainz_id=rg_id,
                    defaults={
                        "artist": db_artist,
                        "title": title,
                        "slug": _unique_slug(Album, f"{title}-{rg_id}"),
                        "mb_primary_type": primary_type,
                        "mb_secondary_types": secondary_types_csv,
                        "release_date": first_release_date,
                        "is_approved": approved,
                    },
                )
                if not created:
                    dirty = False
                    if album_obj.artist_id != db_artist.id:
                        album_obj.artist = db_artist
                        dirty = True
                    if title and album_obj.title != title:
                        album_obj.title = title
                        dirty = True
                    if first_release_date and album_obj.release_date != first_release_date:
                        album_obj.release_date = first_release_date
                        dirty = True
                    if primary_type and album_obj.mb_primary_type != primary_type:
                        album_obj.mb_primary_type = primary_type
                        dirty = True
                    if secondary_types_csv and album_obj.mb_secondary_types != secondary_types_csv:
                        album_obj.mb_secondary_types = secondary_types_csv
                        dirty = True
                    if approved and not album_obj.is_approved:
                        album_obj.is_approved = True
                        dirty = True
                    if dirty:
                        album_obj.save()

                                                                 
            rel_offset = 0
            rel_limit = 25
            releases: list[dict[str, Any]] = []
            while len(releases) < max_releases_per_group:
                try:
                    rel_payload = mb.releases_for_release_group(release_group_mbid=rg_id, limit=rel_limit, offset=rel_offset)
                except MusicBrainzAPIError as e:
                    raise CommandError(str(e))

                rels = rel_payload.get("releases") or []
                if not rels:
                    break

                for r in rels:
                    releases.append(r)
                    if len(releases) >= max_releases_per_group:
                        break

                rel_offset += len(rels)
                total = rel_payload.get("release-count")
                if total is not None and rel_offset >= int(total):
                    break

            if not releases:
                continue

            track_imported_for_album = False
            for rel in releases:
                rel_id = str(rel.get("id") or "").strip()
                if not rel_id:
                    continue

                try:
                    rel_full = mb.release_with_recordings(release_mbid=rel_id)
                except MusicBrainzAPIError:
                    continue

                media = rel_full.get("media") or []
                tracks_flat: list[dict[str, Any]] = []
                for m in media:
                    for t in (m or {}).get("tracks") or []:
                        if t:
                            tracks_flat.append(t)

                if not tracks_flat:
                    continue

                with transaction.atomic():
                    for t in tracks_flat:
                        rec = t.get("recording") or {}
                        rec_id = str(rec.get("id") or "").strip() or None

                        song_title = str(t.get("title") or rec.get("title") or "").strip() or "Unknown Track"
                        position = t.get("position")
                        length_ms = rec.get("length")
                        duration_seconds = 0
                        try:
                            duration_seconds = max(0, int(length_ms or 0) // 1000)
                        except Exception:
                            duration_seconds = 0

                        defaults = {
                            "album": album_obj,
                            "artist": db_artist,
                            "title": song_title,
                            "slug": _unique_slug(Song, f"{song_title}-{rec_id or song_title}"),
                            "track_number": int(position) if position else None,
                            "duration_seconds": duration_seconds,
                            "is_approved": approved,
                        }

                        if rec_id:
                            song_obj, created = Song.objects.get_or_create(
                                musicbrainz_id=rec_id,
                                defaults=defaults,
                            )
                        else:
                                                              
                            song_obj, created = Song.objects.get_or_create(
                                slug=defaults["slug"],
                                defaults=defaults,
                            )

                        if not created:
                            dirty = False
                            if song_obj.album_id != album_obj.id:
                                song_obj.album = album_obj
                                dirty = True
                            if song_obj.artist_id != db_artist.id:
                                song_obj.artist = db_artist
                                dirty = True
                            if song_title and song_obj.title != song_title:
                                song_obj.title = song_title
                                dirty = True
                            if position is not None:
                                try:
                                    pos_i = int(position)
                                except Exception:
                                    pos_i = None
                                if pos_i is not None and song_obj.track_number != pos_i:
                                    song_obj.track_number = pos_i
                                    dirty = True
                            if duration_seconds and song_obj.duration_seconds != duration_seconds:
                                song_obj.duration_seconds = duration_seconds
                                dirty = True
                            if approved and not song_obj.is_approved:
                                song_obj.is_approved = True
                                dirty = True
                            if dirty:
                                song_obj.save()

                        imported_songs += 1

                track_imported_for_album = True
                break

            if track_imported_for_album:
                imported_albums += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Artist={artist_name} (MBID={artist_mbid}) albums={imported_albums} songs={imported_songs}"
            )
        )
