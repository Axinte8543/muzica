from __future__ import annotations

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from music.models import Album, Artist, Genre, Song
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
    help = (
        "Import discography for Spotify artist IDs and mark them as Romanian (is_romanian=true). "
        "This is the recommended way to build a 'Romanian artists' catalog even if they release foreign-language songs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "artist_ids",
            nargs="+",
            type=str,
            help="One or more Spotify artist IDs (not full URLs)",
        )
        parser.add_argument("--market", type=str, default="RO", help="Spotify market, default RO")
        parser.add_argument(
            "--include-groups",
            type=str,
            default="album,single",
            help="Spotify include_groups for artist albums (default: album,single)",
        )
        parser.add_argument(
            "--max-albums",
            type=int,
            default=0,
            help="Stop after importing N albums per artist (0=no limit)",
        )
        parser.add_argument(
            "--approved",
            action="store_true",
            help="Mark imported artists/albums/songs as approved",
        )

    def handle(self, *args, **options):
        artist_ids: list[str] = [str(a).strip() for a in options["artist_ids"] if str(a).strip()]
        market: str = str(options["market"] or "RO").strip() or "RO"
        include_groups: str = str(options["include_groups"] or "album,single").strip() or "album,single"
        max_albums: int = int(options["max_albums"] or 0)
        approved: bool = bool(options["approved"])

        if not artist_ids:
            raise CommandError("Provide at least one artist id")

        try:
            client = SpotifyClient()
        except SpotifyAuthError as e:
            raise CommandError(str(e))

        total_albums = 0
        total_tracks = 0

                                                                                   
                                                                                     
                                                                                  
        tracks_enrichment_forbidden = False

        for artist_id in artist_ids:
            try:
                artist_full = client.get_artist(artist_id)
            except SpotifyAPIError as e:
                raise CommandError(str(e))

            artist_name = str(artist_full.get("name") or "").strip() or "Unknown Artist"
            artist_url = str((artist_full.get("external_urls") or {}).get("spotify") or "").strip()
            artist_img = _pick_image_url(artist_full.get("images"))
            artist_pop = artist_full.get("popularity")

            with transaction.atomic():
                artist_obj = Artist.objects.filter(spotify_id=artist_id).first()
                created = False

                if artist_obj is None:
                                                                                           
                    candidate = Artist.objects.filter(name__iexact=artist_name).first()
                    if candidate is not None and (not candidate.spotify_id or candidate.spotify_id == artist_id):
                        artist_obj = candidate
                    else:
                        artist_obj = Artist(
                            spotify_id=artist_id,
                            name=artist_name,
                            slug=_unique_slug(Artist, artist_name),
                            image_url=artist_img,
                            spotify_url=artist_url,
                            popularity=artist_pop,
                            is_romanian=True,
                            is_approved=approved,
                        )
                        artist_obj.save()
                        created = True

                                                             
                if not artist_obj.spotify_id:
                    artist_obj.spotify_id = artist_id
                    artist_obj.save(update_fields=["spotify_id"])

                if not created:
                    dirty = False
                    if artist_name and artist_obj.name != artist_name:
                        artist_obj.name = artist_name
                        dirty = True
                    if artist_img and artist_obj.image_url != artist_img:
                        artist_obj.image_url = artist_img
                        dirty = True
                    if artist_url and artist_obj.spotify_url != artist_url:
                        artist_obj.spotify_url = artist_url
                        dirty = True
                    if artist_pop is not None and artist_obj.popularity != artist_pop:
                        artist_obj.popularity = artist_pop
                        dirty = True
                    if not artist_obj.is_romanian:
                        artist_obj.is_romanian = True
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

                               
            album_ids: list[str] = []
            offset = 0
            limit = 5
            while True:
                try:
                    page = client.get_artist_albums(
                        artist_id,
                        market=market,
                        include_groups=include_groups,
                        limit=limit,
                        offset=offset,
                    )
                except SpotifyAPIError as e:
                    raise CommandError(str(e))

                items = page.get("items") or []
                if not items:
                    break

                for alb in items:
                    alb_id = str((alb or {}).get("id") or "").strip()
                    if alb_id and alb_id not in album_ids:
                        album_ids.append(alb_id)
                    if max_albums and len(album_ids) >= max_albums:
                        break

                if max_albums and len(album_ids) >= max_albums:
                    break

                offset += len(items)
                total = page.get("total")
                if total is not None and offset >= int(total):
                    break

                                      
            for alb_id in album_ids:
                try:
                    alb_full = client.get_album(alb_id, market=market)
                except SpotifyAPIError as e:
                    raise CommandError(str(e))

                album_title = str(alb_full.get("name") or "").strip() or "Unknown Album"
                album_url = str((alb_full.get("external_urls") or {}).get("spotify") or "").strip()
                album_cover = _pick_image_url(alb_full.get("images"))
                release_date = _parse_release_date(
                    alb_full.get("release_date"),
                    alb_full.get("release_date_precision"),
                )

                with transaction.atomic():
                    album_obj, created = Album.objects.get_or_create(
                        spotify_id=alb_id,
                        defaults={
                            "artist": artist_obj,
                            "title": album_title,
                            "slug": _unique_slug(Album, f"{album_title}-{alb_id}"),
                            "cover_url": album_cover,
                            "spotify_url": album_url,
                            "release_date": release_date,
                            "is_approved": approved,
                        },
                    )
                    if not created:
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

                                                    
                track_ids: list[str] = []
                track_items: list[dict[str, Any]] = []
                t_offset = 0
                t_limit = 50
                while True:
                    try:
                        tpage = client.get_album_tracks(alb_id, market=market, limit=t_limit, offset=t_offset)
                    except SpotifyAPIError as e:
                        raise CommandError(str(e))

                    titems = tpage.get("items") or []
                    if not titems:
                        break

                    for t in titems:
                        tid = str((t or {}).get("id") or "").strip()
                        if tid:
                            track_ids.append(tid)
                            track_items.append(t)

                    t_offset += len(titems)
                    total = tpage.get("total")
                    if total is not None and t_offset >= int(total):
                        break

                if tracks_enrichment_forbidden:
                                                               
                    for t in track_items:
                        track_id = str((t or {}).get("id") or "").strip()
                        if not track_id:
                            continue
                        track_name = str((t or {}).get("name") or "").strip() or "Unknown Track"
                        duration_ms = int((t or {}).get("duration_ms") or 0)
                        duration_seconds = max(0, duration_ms // 1000)
                        track_number = (t or {}).get("track_number")
                        spotify_url = f"https://open.spotify.com/track/{track_id}"

                        with transaction.atomic():
                            song_obj, created = Song.objects.get_or_create(
                                spotify_id=track_id,
                                defaults={
                                    "album": album_obj,
                                    "artist": artist_obj,
                                    "title": track_name,
                                    "slug": _unique_slug(Song, f"{track_name}-{track_id}"),
                                    "track_number": int(track_number) if track_number else None,
                                    "duration_seconds": duration_seconds,
                                    "spotify_url": spotify_url,
                                    "is_approved": approved,
                                },
                            )

                            if not created:
                                dirty = False
                                if song_obj.album_id != album_obj.id:
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
                                if approved and not song_obj.is_approved:
                                    song_obj.is_approved = True
                                    dirty = True
                                if dirty:
                                    song_obj.save()

                            if genres:
                                song_obj.genres.set(genres)

                        total_tracks += 1
                else:
                                                                                  
                    for i in range(0, len(track_ids), 50):
                        batch = track_ids[i : i + 50]
                        try:
                            batch_payload = client.get_tracks(batch, market=market)
                        except SpotifyAPIError as e:
                            msg = str(e)
                            if "403" in msg or "forbidden" in msg.lower():
                                tracks_enrichment_forbidden = True
                                self.stdout.write(
                                    self.style.WARNING(
                                        "Spotify track enrichment disabled (403 Forbidden). "
                                        "Continuing without popularity/preview_url."
                                    )
                                )
                                break
                            raise CommandError(str(e))

                        tracks = batch_payload.get("tracks") or []
                        for tr in tracks:
                            if not tr:
                                continue
                            track_id = str(tr.get("id") or "").strip()
                            if not track_id:
                                continue

                            track_name = str(tr.get("name") or "").strip() or "Unknown Track"
                            spotify_url = str((tr.get("external_urls") or {}).get("spotify") or "").strip()
                            preview_url = str(tr.get("preview_url") or "").strip()
                            duration_ms = int(tr.get("duration_ms") or 0)
                            duration_seconds = max(0, duration_ms // 1000)
                            track_number = tr.get("track_number")
                            popularity = tr.get("popularity")

                            with transaction.atomic():
                                song_obj, created = Song.objects.get_or_create(
                                    spotify_id=track_id,
                                    defaults={
                                        "album": album_obj,
                                        "artist": artist_obj,
                                        "title": track_name,
                                        "slug": _unique_slug(Song, f"{track_name}-{track_id}"),
                                        "track_number": int(track_number) if track_number else None,
                                        "duration_seconds": duration_seconds,
                                        "spotify_url": spotify_url,
                                        "preview_url": preview_url,
                                        "popularity": popularity,
                                        "is_approved": approved,
                                    },
                                )

                                if not created:
                                    dirty = False
                                    if song_obj.album_id != album_obj.id:
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

                            total_tracks += 1

                                                                                                    
                    if tracks_enrichment_forbidden:
                        for t in track_items:
                            track_id = str((t or {}).get("id") or "").strip()
                            if not track_id:
                                continue
                            if Song.objects.filter(spotify_id=track_id).exists():
                                continue
                            track_name = str((t or {}).get("name") or "").strip() or "Unknown Track"
                            duration_ms = int((t or {}).get("duration_ms") or 0)
                            duration_seconds = max(0, duration_ms // 1000)
                            track_number = (t or {}).get("track_number")
                            spotify_url = f"https://open.spotify.com/track/{track_id}"
                            with transaction.atomic():
                                song_obj = Song.objects.create(
                                    spotify_id=track_id,
                                    album=album_obj,
                                    artist=artist_obj,
                                    title=track_name,
                                    slug=_unique_slug(Song, f"{track_name}-{track_id}"),
                                    track_number=int(track_number) if track_number else None,
                                    duration_seconds=duration_seconds,
                                    spotify_url=spotify_url,
                                    is_approved=approved,
                                )
                                if genres:
                                    song_obj.genres.set(genres)
                            total_tracks += 1

                total_albums += 1

            self.stdout.write(self.style.SUCCESS(f"Imported artist: {artist_name} ({artist_id})"))

        self.stdout.write(self.style.SUCCESS(f"Done. Albums: {total_albums}, Tracks: {total_tracks}"))
