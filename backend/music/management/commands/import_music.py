from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.utils.text import slugify

from music.lastfm import LastFMAPIError, LastFMClient
from music.musicbrainz import MusicBrainzAPIError, MusicBrainzClient
from music.models import Album, Artist, ArtistSimilarity, Genre, Song
from music.spotify import SpotifyAPIError, SpotifyAuthError, SpotifyClient


def _normalize_name(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _norm_key(value: str) -> str:
    return slugify(_normalize_name(value))


def _safe_first_image_url(images: Any) -> str:
    if not isinstance(images, list) or not images:
        return ""
    first = images[0]
    if not isinstance(first, dict):
        return ""
    return str(first.get("url") or "").strip()


def _get_or_create_genre(name: str) -> Genre:
    clean = _normalize_name(name)
    if not clean:
        raise ValueError("Empty genre")

    slug = slugify(clean)
    if not slug:
        slug = "genre"

    obj, _ = Genre.objects.get_or_create(
        name=clean,
        defaults={"slug": slug},
    )
                                                             
    return obj


def _unique_slug(model, base: str) -> str:
    base_slug = slugify(_normalize_name(base))
    if not base_slug:
        base_slug = "item"

    slug = base_slug
    suffix = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


def _resolve_musicbrainz_artist_mbid(*, name: str, romanian_only: bool) -> tuple[str, str]:
                                                                       
    mb = MusicBrainzClient()
    clean = _normalize_name(name)
    if not clean:
        raise CommandError("Empty artist name")

    def _artist_field(term: str) -> str:
                                                                                
                                                                                      
        safe = term.replace('"', "\\\"")
        if " " in safe or any(not (ch.isalnum() or ch in {"-", "_"}) for ch in safe):
            return f'artist:"{safe}"'
        return f"artist:{safe}"

    artist_q = _artist_field(clean)

                                                                              
                                                                        
                                                                      
    is_ambiguous_name = (" " not in clean) and (len(clean) <= 5)

    queries: list[str] = []
    if romanian_only or is_ambiguous_name:
                                                                                
                                                        
        queries.extend(
            [
                f"{artist_q} AND country:RO",
                f"{artist_q} AND area:Romania",
            ]
        )

    if romanian_only:
                                                               
        queries.append(f"{artist_q} AND romanian")

    queries.append(artist_q)

    search_limit = 100 if is_ambiguous_name else 25

    artist_list: list[dict[str, Any]] = []
    last_err: Exception | None = None
    for q in queries:
        try:
            payload = mb.search_artist(name=clean, query=q, limit=search_limit)
        except MusicBrainzAPIError as e:
            last_err = e
            continue
        artist_list = payload.get("artists") or []
        if artist_list:
            break

    if not artist_list:
        if last_err is not None:
            raise CommandError(str(last_err))
        raise CommandError(f"No artists found on MusicBrainz for: {clean}")
    if not artist_list:
        raise CommandError(f"No artists found on MusicBrainz for: {clean}")

    def is_romania(a: dict[str, Any]) -> bool:
        if str(a.get("country") or "").strip().upper() == "RO":
            return True
        area = a.get("area") or {}
        area_name = str(area.get("name") or "").strip().lower()
        if area_name == "romania":
            return True
        dis = str(a.get("disambiguation") or "").strip().lower()
        if "romanian" in dis:
            return True
        return False

    def score(a: dict[str, Any]) -> tuple[int, int, int, int]:
        n = str(a.get("name") or "").strip().lower()
        exact = 1 if n == clean.lower() else 0
        ro = 1 if is_romania(a) else 0
        typ = str(a.get("type") or "").strip().lower()
        is_group = 1 if typ == "group" else 0
        return (exact, ro, is_group, int(a.get("score") or 0))

    artist_list.sort(key=score, reverse=True)
    best = artist_list[0]

    mbid = str(best.get("id") or "").strip()
    resolved_name = str(best.get("name") or "").strip() or clean
    if not mbid:
        raise CommandError(f"MusicBrainz artist missing id for: {clean}")
    return mbid, resolved_name


@dataclass
class ImportStats:
    artists: int = 0
    albums: int = 0
    songs: int = 0
    spotify_enriched_artists: int = 0
    spotify_enriched_albums: int = 0
    spotify_enriched_songs: int = 0
    lastfm_edges: int = 0


class Command(BaseCommand):
    help = (
        "Import Romanian artists using MusicBrainz for discography, "
        "Spotify for images/genres/popularity, and Last.fm for similar artists."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--artists",
            type=str,
            default="",
            help="Comma-separated list of Romanian artist names (e.g., 'Nane, Azteca')",
        )
        parser.add_argument(
            "--artists-file",
            type=str,
            default="",
            help="Path to a text file with one artist name per line",
        )
        parser.add_argument(
            "--all-existing",
            action="store_true",
            help="Process all artists currently present in the local database",
        )
        parser.add_argument(
            "--start-after",
            type=str,
            default="",
            help="When processing a list, skip artists through this name and start after it",
        )
        parser.add_argument(
            "--market",
            type=str,
            default="RO",
            help="Spotify market (default RO)",
        )
        parser.add_argument(
            "--max-release-groups",
            type=int,
            default=25,
            help="MusicBrainz: max release-groups per artist (default 25)",
        )
        parser.add_argument(
            "--max-releases-per-group",
            type=int,
            default=5,
            help="MusicBrainz: releases inspected per release-group (default 5)",
        )
        parser.add_argument(
            "--musicbrainz-romanian-only",
            action="store_true",
            help="MusicBrainz: during search, require area:Romania (may skip Moldova/other matches)",
        )
        parser.add_argument(
            "--approved",
            action="store_true",
            help="Mark imported artists/albums/songs as approved",
        )
        parser.add_argument(
            "--skip-spotify",
            action="store_true",
            help="Skip Spotify enrichment step",
        )
        parser.add_argument(
            "--with-lastfm",
            action="store_true",
            help="Also store similar artists from Last.fm (requires LASTFM_API_KEY)",
        )
        parser.add_argument(
            "--lastfm-limit",
            type=int,
            default=10,
            help="Last.fm: similar artists limit per artist (default 10)",
        )

    def handle(self, *args, **options):
        raw_artists = str(options.get("artists") or "").strip()
        artists_file = str(options.get("artists_file") or "").strip()
        all_existing = bool(options.get("all_existing"))
        start_after = _normalize_name(options.get("start_after") or "")
        market = str(options.get("market") or "RO").strip() or "RO"
        max_release_groups = int(options.get("max_release_groups") or 25)
        max_releases_per_group = int(options.get("max_releases_per_group") or 5)
        mb_romanian_only = bool(options.get("musicbrainz_romanian_only"))
        approved = bool(options.get("approved"))
        skip_spotify = bool(options.get("skip_spotify"))
        with_lastfm = bool(options.get("with_lastfm"))
        lastfm_limit = max(1, int(options.get("lastfm_limit") or 10))

        names: list[str] = []
        if all_existing:
            names.extend(
                Artist.objects.order_by("name", "id").values_list("name", flat=True)
            )
        if raw_artists:
            names.extend([_normalize_name(x) for x in raw_artists.split(",") if _normalize_name(x)])
        if artists_file:
            if not os.path.exists(artists_file):
                raise CommandError(f"artists-file not found: {artists_file}")
            with open(artists_file, "r", encoding="utf-8") as f:
                for line in f:
                    n = _normalize_name(line)
                    if n and not n.startswith("#"):
                        names.append(n)

                                 
        seen: set[str] = set()
        romanian_artists = []
        for n in names:
            key = n.lower()
            if key in seen:
                continue
            seen.add(key)
            romanian_artists.append(n)

        if start_after:
            start_key = start_after.lower()
            while romanian_artists and romanian_artists[0].lower() <= start_key:
                romanian_artists.pop(0)

        if not romanian_artists:
            raise CommandError("Provide --artists, --artists-file, or --all-existing")

        spotify: SpotifyClient | None = None
        if not skip_spotify:
            try:
                spotify = SpotifyClient()
            except SpotifyAuthError as e:
                self.stdout.write(self.style.WARNING(f"Spotify disabled: {e}"))
                spotify = None

        lastfm: LastFMClient | None = None
        if with_lastfm:
            try:
                lastfm = LastFMClient()
            except LastFMAPIError as e:
                self.stdout.write(self.style.WARNING(f"Last.fm disabled: {e}"))
                lastfm = None

        stats = ImportStats()

                                                                                
                                                                              
                                                           
        self._spotify_tracks_forbidden = False
                                                                              
                                                                             
                                                             
        self._spotify_disabled = False

        for artist_name in romanian_artists:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Importing {artist_name} (MusicBrainz)..."))

            try:
                artist_mbid, resolved_name = _resolve_musicbrainz_artist_mbid(
                    name=artist_name,
                    romanian_only=mb_romanian_only,
                )
            except CommandError as e:
                self.stdout.write(self.style.WARNING(str(e)))
                continue

            call_command(
                "import_musicbrainz_artist",
                resolved_name,
                mbid=artist_mbid,
                romanian_only=False,
                force_romanian=True,
                max_release_groups=max_release_groups,
                max_releases_per_group=max_releases_per_group,
                approved=approved,
                verbosity=0,
            )

            try:
                db_artist = Artist.objects.get(musicbrainz_id=str(artist_mbid).strip())
            except Artist.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"DB artist not found after import: {artist_name} ({artist_mbid})"))
                continue

            stats.artists += 1
            stats.albums += Album.objects.filter(artist=db_artist).count()
            stats.songs += Song.objects.filter(artist=db_artist).count()

            if spotify:
                self._enrich_with_spotify(
                    spotify=spotify,
                    artist=db_artist,
                    market=market,
                    approved=approved,
                    stats=stats,
                )

            if lastfm:
                self._store_lastfm_similar(lastfm=lastfm, artist=db_artist, limit=lastfm_limit, stats=stats)

        self.stdout.write(
            self.style.SUCCESS(
                "Done. "
                f"artists={stats.artists} albums={stats.albums} songs={stats.songs} "
                f"spotify(artists={stats.spotify_enriched_artists}, albums={stats.spotify_enriched_albums}, songs={stats.spotify_enriched_songs}) "
                f"lastfm_edges={stats.lastfm_edges}"
            )
        )

    def _enrich_with_spotify(
        self,
        *,
        spotify: SpotifyClient,
        artist: Artist,
        market: str,
        approved: bool,
        stats: ImportStats,
    ) -> None:
        if getattr(self, "_spotify_disabled", False):
            return

        try:
            candidates = spotify.search_artist(name=artist.name, market=market, limit=5)
        except SpotifyAPIError as e:
            msg = str(e)
            if "429" in msg or "rate limit" in msg.lower():
                if not getattr(self, "_spotify_disabled", False):
                    self._spotify_disabled = True
                    self.stdout.write(
                        self.style.WARNING(
                            "Spotify disabled for this run due to rate limit (429). "
                            f"Details: {msg}. "
                            "Re-run later, or run now with --skip-spotify."
                        )
                    )
                return
            self.stdout.write(self.style.WARNING(f"Spotify search failed for {artist.name}: {e}"))
            return

        if not candidates:
            self.stdout.write(self.style.WARNING(f"Spotify: no artist match for {artist.name}"))
            return

                                                                       
        best = None
        for c in candidates:
            if str(c.get("name") or "").strip().lower() == artist.name.strip().lower():
                best = c
                break
        if best is None:
            best = candidates[0]

        spotify_artist_id = str(best.get("id") or "").strip()
        spotify_url = str(((best.get("external_urls") or {}).get("spotify")) or "").strip()
        popularity = best.get("popularity")
        image_url = _safe_first_image_url(best.get("images"))
        genres = best.get("genres") or []

        if spotify_artist_id:
            existing = (
                Artist.objects.filter(spotify_id=spotify_artist_id)
                .exclude(pk=artist.pk)
                .only("id", "name")
                .first()
            )
            if existing is not None:
                self.stdout.write(
                    self.style.WARNING(
                        "Spotify: artist id collision for "
                        f"{artist.name} -> {spotify_artist_id} already used by {existing.name}. "
                        "Skipping Spotify enrichment for this artist."
                    )
                )
                return

        try:
            with transaction.atomic():
                dirty = False
                if spotify_artist_id and artist.spotify_id != spotify_artist_id:
                    artist.spotify_id = spotify_artist_id
                    dirty = True
                if spotify_url and artist.spotify_url != spotify_url:
                    artist.spotify_url = spotify_url
                    dirty = True
                if popularity is not None:
                    try:
                        pop_i = int(popularity)
                    except Exception:
                        pop_i = None
                    if pop_i is not None and artist.popularity != pop_i:
                        artist.popularity = pop_i
                        dirty = True
                if image_url and not artist.image_url:
                    artist.image_url = image_url
                    dirty = True
                if approved and not artist.is_approved:
                    artist.is_approved = True
                    dirty = True
                if dirty:
                    artist.save()

                if isinstance(genres, list) and genres:
                    genre_objs = []
                    for g in genres:
                        try:
                            genre_objs.append(_get_or_create_genre(str(g)))
                        except Exception:
                            continue
                    if genre_objs:
                        artist.genres.add(*genre_objs)
        except IntegrityError as e:
            self.stdout.write(
                self.style.WARNING(
                    f"Spotify: failed to save artist {artist.name} due to integrity error: {e}. "
                    "Continuing without Spotify enrichment for this artist."
                )
            )
            return

        stats.spotify_enriched_artists += 1

        if not spotify_artist_id:
            return

                                                                 
        try:
            spotify_albums = self._fetch_all_spotify_artist_albums(
                spotify=spotify,
                artist_id=spotify_artist_id,
                market=market,
            )
        except SpotifyAPIError as e:
            msg = str(e)
            if "429" in msg or "rate limit" in msg.lower():
                if not getattr(self, "_spotify_disabled", False):
                    self._spotify_disabled = True
                    self.stdout.write(
                        self.style.WARNING(
                            "Spotify disabled for this run due to rate limit (429). "
                            f"Details: {msg}. "
                            "Re-run later, or run now with --skip-spotify."
                        )
                    )
                return
            self.stdout.write(self.style.WARNING(f"Spotify albums failed for {artist.name}: {e}"))
            return

        db_albums = list(Album.objects.filter(artist=artist))
        db_album_by_key: dict[str, list[Album]] = {}
        for a in db_albums:
            db_album_by_key.setdefault(_norm_key(a.title), []).append(a)

        matched_album_pairs: list[tuple[Album, dict[str, Any]]] = []
        for sa in spotify_albums:
            title = str(sa.get("name") or "").strip()
            if not title:
                continue
            key = _norm_key(title)
            candidates_db = db_album_by_key.get(key) or []
            if not candidates_db:
                continue
                                      
            matched_album_pairs.append((candidates_db[0], sa))

                                                                   
        for db_album, sa in matched_album_pairs:
            images = sa.get("images")
            cover_url = _safe_first_image_url(images)
            album_spotify_id = str(sa.get("id") or "").strip()
            album_spotify_url = str(((sa.get("external_urls") or {}).get("spotify")) or "").strip()

            if album_spotify_id:
                existing_album = (
                    Album.objects.filter(spotify_id=album_spotify_id)
                    .exclude(pk=db_album.pk)
                    .only("id", "title")
                    .first()
                )
                if existing_album is not None:
                    self.stdout.write(
                        self.style.WARNING(
                            "Spotify: album id collision for "
                            f"{artist.name} / {db_album.title} -> {album_spotify_id} already used by {existing_album.title}. "
                            "Skipping spotify_id update for this album."
                        )
                    )
                    album_spotify_id = ""

            try:
                with transaction.atomic():
                    dirty = False
                    if cover_url and not db_album.cover_url:
                        db_album.cover_url = cover_url
                        dirty = True
                    if album_spotify_id and db_album.spotify_id != album_spotify_id:
                        db_album.spotify_id = album_spotify_id
                        dirty = True
                    if album_spotify_url and db_album.spotify_url != album_spotify_url:
                        db_album.spotify_url = album_spotify_url
                        dirty = True
                    if approved and not db_album.is_approved:
                        db_album.is_approved = True
                        dirty = True
                    if dirty:
                        db_album.save()
            except IntegrityError as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"Spotify: failed to save album {artist.name} / {db_album.title} due to integrity error: {e}. "
                        "Continuing."
                    )
                )
                continue

            stats.spotify_enriched_albums += 1

            if album_spotify_id:
                self._enrich_album_songs_with_spotify(
                    spotify=spotify,
                    db_album=db_album,
                    market=market,
                    approved=approved,
                    stats=stats,
                )

    def _fetch_all_spotify_artist_albums(self, *, spotify: SpotifyClient, artist_id: str, market: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        offset = 0
        limit = 5
        while True:
            payload = spotify.get_artist_albums(artist_id, market=market, limit=limit, offset=offset)
            page = payload.get("items") or []
            if not isinstance(page, list) or not page:
                break
            for it in page:
                if isinstance(it, dict):
                    items.append(it)
            offset += len(page)
            total = payload.get("total")
            if total is not None and offset >= int(total):
                break
            if len(page) < limit:
                break

                      
        seen: set[str] = set()
        uniq: list[dict[str, Any]] = []
        for it in items:
            _id = str(it.get("id") or "").strip()
            if not _id or _id in seen:
                continue
            seen.add(_id)
            uniq.append(it)
        return uniq

    def _enrich_album_songs_with_spotify(
        self,
        *,
        spotify: SpotifyClient,
        db_album: Album,
        market: str,
        approved: bool,
        stats: ImportStats,
    ) -> None:
        if getattr(self, "_spotify_tracks_forbidden", False):
            return
        if getattr(self, "_spotify_disabled", False):
            return

                                           
        track_items: list[dict[str, Any]] = []
        offset = 0
        limit = 50
        while True:
            try:
                payload = spotify.get_album_tracks(str(db_album.spotify_id), market=market, limit=limit, offset=offset)
            except SpotifyAPIError as e:
                msg = str(e)
                if "429" in msg or "rate limit" in msg.lower():
                    if not getattr(self, "_spotify_disabled", False):
                        self._spotify_disabled = True
                        self.stdout.write(
                            self.style.WARNING(
                                "Spotify disabled for this run due to rate limit (429). "
                                f"Details: {msg}. "
                                "Re-run later, or run now with --skip-spotify."
                            )
                        )
                    return
                raise
            page = payload.get("items") or []
            if not isinstance(page, list) or not page:
                break
            for it in page:
                if isinstance(it, dict):
                    track_items.append(it)
            offset += len(page)
            total = payload.get("total")
            if total is not None and offset >= int(total):
                break
            if len(page) < limit:
                break

        track_ids = [str(t.get("id") or "").strip() for t in track_items if str(t.get("id") or "").strip()]
        if not track_ids:
            return

                                                          
        by_id: dict[str, dict[str, Any]] = {}
        try:
            for i in range(0, len(track_ids), 50):
                chunk = track_ids[i : i + 50]
                payload = spotify.get_tracks(chunk, market=market)
                tracks = payload.get("tracks") or []
                if not isinstance(tracks, list):
                    continue
                for tr in tracks:
                    if isinstance(tr, dict) and tr.get("id"):
                        by_id[str(tr.get("id"))] = tr
        except SpotifyAPIError as e:
                                                                                 
                                                                       
            msg = str(e)
            if "429" in msg or "rate limit" in msg.lower():
                if not getattr(self, "_spotify_disabled", False):
                    self._spotify_disabled = True
                    self.stdout.write(
                        self.style.WARNING(
                            "Spotify disabled for this run due to rate limit (429). "
                            f"Details: {msg}. "
                            "Re-run later, or run now with --skip-spotify."
                        )
                    )
                return
            if "Spotify API error: 403" in msg or "\"status\": 403" in msg:
                self._spotify_tracks_forbidden = True
                self.stdout.write(
                    self.style.WARNING(
                        "Spotify track enrichment disabled (403 Forbidden). "
                        "Continuing without popularity/preview_url."
                    )
                )
                return
            raise

                                                                        
        db_songs = list(Song.objects.filter(album=db_album).select_related("artist"))
        db_by_track: dict[int, Song] = {}
        db_by_title: dict[str, Song] = {}
        for s in db_songs:
            if s.track_number is not None and s.track_number not in db_by_track:
                db_by_track[int(s.track_number)] = s
            key = _norm_key(s.title)
            if key and key not in db_by_title:
                db_by_title[key] = s

        for t in track_items:
            t_id = str(t.get("id") or "").strip()
            if not t_id:
                continue
            tr_full = by_id.get(t_id) or {}
            title = str(t.get("name") or "").strip()
            track_no = t.get("track_number")
            try:
                track_no_i = int(track_no) if track_no is not None else None
            except Exception:
                track_no_i = None

            db_song = None
            if track_no_i is not None:
                db_song = db_by_track.get(track_no_i)
            if db_song is None and title:
                db_song = db_by_title.get(_norm_key(title))
            if db_song is None:
                continue

            spotify_url = str(((tr_full.get("external_urls") or {}).get("spotify")) or "").strip()
            preview_url = str(tr_full.get("preview_url") or "").strip()
            popularity = tr_full.get("popularity")

            if t_id:
                existing_song = (
                    Song.objects.filter(spotify_id=t_id)
                    .exclude(pk=db_song.pk)
                    .only("id", "title")
                    .first()
                )
                if existing_song is not None:
                    self.stdout.write(
                        self.style.WARNING(
                            "Spotify: song id collision for "
                            f"{db_album.artist.name} / {db_album.title} / {db_song.title} -> {t_id}. "
                            "Skipping spotify_id update for this song."
                        )
                    )
                    t_id = ""

            try:
                with transaction.atomic():
                    dirty = False
                    if t_id and db_song.spotify_id != t_id:
                        db_song.spotify_id = t_id
                        dirty = True
                    if spotify_url and db_song.spotify_url != spotify_url:
                        db_song.spotify_url = spotify_url
                        dirty = True
                    if preview_url and db_song.preview_url != preview_url:
                        db_song.preview_url = preview_url
                        dirty = True
                    if popularity is not None:
                        try:
                            pop_i = int(popularity)
                        except Exception:
                            pop_i = None
                        if pop_i is not None and db_song.popularity != pop_i:
                            db_song.popularity = pop_i
                            dirty = True
                    if approved and not db_song.is_approved:
                        db_song.is_approved = True
                        dirty = True
                    if dirty:
                        db_song.save()
            except IntegrityError as e:
                self.stdout.write(
                    self.style.WARNING(
                        f"Spotify: failed to save song {db_album.artist.name} / {db_album.title} / {db_song.title} "
                        f"due to integrity error: {e}. Continuing."
                    )
                )
                continue

            stats.spotify_enriched_songs += 1

    def _store_lastfm_similar(self, *, lastfm: LastFMClient, artist: Artist, limit: int, stats: ImportStats) -> None:
        try:
            items = lastfm.get_similar_artists(artist_name=artist.name, limit=limit)
        except LastFMAPIError as e:
            self.stdout.write(self.style.WARNING(f"Last.fm failed for {artist.name}: {e}"))
            return

        for it in items:
            name = _normalize_name(it.get("name") or "")
            if not name or name.lower() == artist.name.lower():
                continue

            match_val = it.get("match")
            try:
                match_f = float(match_val) if match_val is not None else None
            except Exception:
                match_f = None

            with transaction.atomic():
                to_artist, _ = Artist.objects.get_or_create(
                    name=name,
                    defaults={
                        "slug": _unique_slug(Artist, name),
                        "is_approved": False,
                        "is_romanian": True,
                    },
                )

                edge, created = ArtistSimilarity.objects.get_or_create(
                    from_artist=artist,
                    to_artist=to_artist,
                    source="lastfm",
                    defaults={"match": match_f},
                )
                if not created and match_f is not None and edge.match != match_f:
                    edge.match = match_f
                    edge.save()

            stats.lastfm_edges += 1
