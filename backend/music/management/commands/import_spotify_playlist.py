from __future__ import annotations

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from music.models import Album, Artist, Genre, Song, SongFeature
from music.spotify import SpotifyClient, SpotifyAPIError, SpotifyAuthError


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


def _pick_image_url(images: list[dict[str, Any]] | None) -> str:
    images = images or []
    if not images:
        return ""
                                                              
    return str(images[0].get("url") or "").strip()


def _parse_release_date(raw: str | None, precision: str | None) -> date:
    raw = (raw or "").strip()
    precision = (precision or "").strip().lower()

    if not raw:
        return date(1970, 1, 1)

    try:
        if precision == "day":
            yyyy, mm, dd = raw.split("-")
            return date(int(yyyy), int(mm), int(dd))
        if precision == "month":
            yyyy, mm = raw.split("-")
            return date(int(yyyy), int(mm), 1)
        if precision == "year":
            return date(int(raw), 1, 1)

                                        
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


class Command(BaseCommand):
    help = "Import tracks (artists/albums/songs) from a Spotify playlist into the local DB."

    def add_arguments(self, parser):
        parser.add_argument("playlist_id", type=str, help="Spotify playlist ID (not the full URL)")
        parser.add_argument("--market", type=str, default="RO", help="Spotify market, default RO")
        parser.add_argument(
            "--max-tracks",
            type=int,
            default=0,
            help="Stop after importing N tracks (0 = no limit)",
        )
        parser.add_argument(
            "--approved",
            action="store_true",
            help="Mark imported artists/albums/songs as approved",
        )

    def handle(self, *args, **options):
        playlist_id: str = options["playlist_id"].strip()
        market: str = options["market"].strip() or "RO"
        max_tracks: int = int(options["max_tracks"] or 0)
        approved: bool = bool(options["approved"])

        if not playlist_id:
            raise CommandError("playlist_id is required")

        try:
            client = SpotifyClient()
        except SpotifyAuthError as e:
            raise CommandError(str(e))

        artist_cache: dict[str, dict[str, Any]] = {}

        imported = 0
        offset = 0
        limit = 100

        while True:
            try:
                payload = client.get_playlist_tracks(playlist_id, market=market, limit=limit, offset=offset)
            except SpotifyAPIError as e:
                raise CommandError(str(e))

            items = payload.get("items") or []
            if not items:
                break

            for item in items:
                track = (item or {}).get("track")
                if not track or track.get("is_local"):
                    continue

                if track.get("type") != "track":
                    continue

                spotify_track_id = str(track.get("id") or "").strip()
                if not spotify_track_id:
                    continue

                album_data = track.get("album") or {}
                spotify_album_id = str(album_data.get("id") or "").strip()

                artists = track.get("artists") or []
                if not artists:
                    continue

                primary_artist_data = artists[0] or {}
                spotify_artist_id = str(primary_artist_data.get("id") or "").strip()
                if not spotify_artist_id:
                    continue

                featured_artist_ids: list[str] = []
                for a in artists[1:]:
                    a_id = str((a or {}).get("id") or "").strip()
                    if not a_id:
                        continue
                    if a_id == spotify_artist_id:
                        continue
                    if a_id not in featured_artist_ids:
                        featured_artist_ids.append(a_id)

                if spotify_artist_id in artist_cache:
                    artist_full = artist_cache[spotify_artist_id]
                else:
                    try:
                        artist_full = client.get_artist(spotify_artist_id)
                    except SpotifyAPIError as e:
                        raise CommandError(str(e))
                    artist_cache[spotify_artist_id] = artist_full

                with transaction.atomic():
                    artist_obj, artist_created = Artist.objects.get_or_create(
                        spotify_id=spotify_artist_id,
                        defaults={
                            "name": str(artist_full.get("name") or "").strip() or "Unknown Artist",
                            "slug": _unique_slug(Artist, artist_full.get("name") or spotify_artist_id),
                            "image_url": _pick_image_url(artist_full.get("images")),
                            "spotify_url": str((artist_full.get("external_urls") or {}).get("spotify") or "").strip(),
                            "popularity": artist_full.get("popularity"),
                            "is_approved": approved,
                        },
                    )

                    if not artist_created:
                        dirty = False
                        new_name = str(artist_full.get("name") or "").strip()
                        if new_name and artist_obj.name != new_name:
                            artist_obj.name = new_name
                            dirty = True

                        new_img = _pick_image_url(artist_full.get("images"))
                        if new_img and artist_obj.image_url != new_img:
                            artist_obj.image_url = new_img
                            dirty = True

                        new_url = str((artist_full.get("external_urls") or {}).get("spotify") or "").strip()
                        if new_url and artist_obj.spotify_url != new_url:
                            artist_obj.spotify_url = new_url
                            dirty = True

                        new_pop = artist_full.get("popularity")
                        if new_pop is not None and artist_obj.popularity != new_pop:
                            artist_obj.popularity = new_pop
                            dirty = True

                        if approved and not artist_obj.is_approved:
                            artist_obj.is_approved = True
                            dirty = True

                        if dirty:
                            artist_obj.save()

                    genre_names: list[str] = [
                        str(g).strip() for g in (artist_full.get("genres") or []) if str(g).strip()
                    ]
                    genres: list[Genre] = []
                    for gname in genre_names:
                        gslug = slugify(gname)
                        if not gslug:
                            continue
                        genre_obj, _ = Genre.objects.get_or_create(slug=gslug, defaults={"name": gname})
                        if genre_obj.name != gname:
                            genre_obj.name = gname
                            genre_obj.save(update_fields=["name"])
                        genres.append(genre_obj)

                    if genres:
                        artist_obj.genres.set(genres)

                    album_obj = None
                    if spotify_album_id:
                        release_date = _parse_release_date(
                            album_data.get("release_date"),
                            album_data.get("release_date_precision"),
                        )
                        album_title = str(album_data.get("name") or "").strip() or "Unknown Album"
                        album_cover = _pick_image_url(album_data.get("images"))
                        album_url = str((album_data.get("external_urls") or {}).get("spotify") or "").strip()

                        album_obj, album_created = Album.objects.get_or_create(
                            spotify_id=spotify_album_id,
                            defaults={
                                "artist": artist_obj,
                                "title": album_title,
                                "slug": _unique_slug(Album, f"{album_title}-{spotify_album_id}"),
                                "cover_url": album_cover,
                                "spotify_url": album_url,
                                "release_date": release_date,
                                "is_approved": approved,
                            },
                        )

                        if not album_created:
                            dirty = False
                            if album_obj.artist_id != artist_obj.id:
                                album_obj.artist = artist_obj
                                dirty = True
                            if album_title and album_obj.title != album_title:
                                album_obj.title = album_title
                                dirty = True
                            if album_cover and album_obj.cover_url != album_cover:
                                album_obj.cover_url = album_cover
                                dirty = True
                            if album_url and album_obj.spotify_url != album_url:
                                album_obj.spotify_url = album_url
                                dirty = True
                            if release_date and album_obj.release_date != release_date:
                                album_obj.release_date = release_date
                                dirty = True
                            if approved and not album_obj.is_approved:
                                album_obj.is_approved = True
                                dirty = True
                            if dirty:
                                album_obj.save()

                        if genres:
                            album_obj.genres.set(genres)

                    track_name = str(track.get("name") or "").strip() or "Unknown Track"
                    spotify_url = str((track.get("external_urls") or {}).get("spotify") or "").strip()
                    preview_url = str(track.get("preview_url") or "").strip()
                    duration_ms = int(track.get("duration_ms") or 0)
                    duration_seconds = max(0, duration_ms // 1000)
                    track_number = track.get("track_number")
                    popularity = track.get("popularity")

                    song_obj, song_created = Song.objects.get_or_create(
                        spotify_id=spotify_track_id,
                        defaults={
                            "album": album_obj,
                            "artist": artist_obj,
                            "title": track_name,
                            "slug": _unique_slug(Song, f"{track_name}-{spotify_track_id}"),
                            "track_number": int(track_number) if track_number else None,
                            "duration_seconds": duration_seconds,
                            "spotify_url": spotify_url,
                            "preview_url": preview_url,
                            "popularity": popularity,
                            "is_approved": approved,
                        },
                    )

                    if not song_created:
                        dirty = False
                        if song_obj.album_id != (album_obj.id if album_obj else None):
                            song_obj.album = album_obj
                            dirty = True
                        if song_obj.artist_id != artist_obj.id:
                            song_obj.artist = artist_obj
                            dirty = True
                        if track_name and song_obj.title != track_name:
                            song_obj.title = track_name
                            dirty = True
                        if track_number is not None:
                            tn = int(track_number)
                            if song_obj.track_number != tn:
                                song_obj.track_number = tn
                                dirty = True
                        if duration_seconds and song_obj.duration_seconds != duration_seconds:
                            song_obj.duration_seconds = duration_seconds
                            dirty = True
                        if spotify_url and song_obj.spotify_url != spotify_url:
                            song_obj.spotify_url = spotify_url
                            dirty = True
                        if preview_url and song_obj.preview_url != preview_url:
                            song_obj.preview_url = preview_url
                            dirty = True
                        if popularity is not None and song_obj.popularity != popularity:
                            song_obj.popularity = popularity
                            dirty = True
                        if approved and not song_obj.is_approved:
                            song_obj.is_approved = True
                            dirty = True

                        if dirty:
                            song_obj.save()

                    if genres:
                        song_obj.genres.set(genres)

                                                                                         
                    if featured_artist_ids:
                        for featured_id in featured_artist_ids:
                            if featured_id in artist_cache:
                                featured_full = artist_cache[featured_id]
                            else:
                                try:
                                    featured_full = client.get_artist(featured_id)
                                except SpotifyAPIError as e:
                                    raise CommandError(str(e))
                                artist_cache[featured_id] = featured_full

                            featured_obj, featured_created = Artist.objects.get_or_create(
                                spotify_id=featured_id,
                                defaults={
                                    "name": str(featured_full.get("name") or "").strip() or "Unknown Artist",
                                    "slug": _unique_slug(Artist, featured_full.get("name") or featured_id),
                                    "image_url": _pick_image_url(featured_full.get("images")),
                                    "spotify_url": str((featured_full.get("external_urls") or {}).get("spotify") or "").strip(),
                                    "popularity": featured_full.get("popularity"),
                                    "is_approved": approved,
                                },
                            )
                            if not featured_created:
                                if approved and not featured_obj.is_approved:
                                    featured_obj.is_approved = True
                                    featured_obj.save(update_fields=["is_approved"])

                            SongFeature.objects.get_or_create(song=song_obj, artist=featured_obj)

                imported += 1
                if imported % 50 == 0:
                    self.stdout.write(self.style.SUCCESS(f"Imported {imported} tracks so far..."))

                if max_tracks and imported >= max_tracks:
                    self.stdout.write(self.style.SUCCESS(f"Done. Imported {imported} tracks."))
                    return

            offset += len(items)
            total = payload.get("total")
            if total is not None and offset >= int(total):
                break

        self.stdout.write(self.style.SUCCESS(f"Done. Imported {imported} tracks."))
