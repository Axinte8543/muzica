from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

from music.models import Artist, Song, SongFeature
from music.integrations import MusicExternalIntegrationService, SpotifyAPIError, SpotifyAuthError


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


def _extract_spotify_track_id(*, spotify_id: str | None, spotify_url: str | None) -> str:
	spotify_id = str(spotify_id or "").strip()
	if spotify_id:
		return spotify_id

	url = str(spotify_url or "").strip()
	if not url:
		return ""

	# Accept spotify:track:<id>
	if url.startswith("spotify:track:"):
		return url.split(":")[-1].strip()

	# Accept https://open.spotify.com/track/<id>?...
	try:
		parsed = urlparse(url)
	except Exception:
		return ""

	path = str(parsed.path or "").strip("/")
	parts = path.split("/")
	if len(parts) >= 2 and parts[0] == "track":
		return str(parts[1]).strip()
	return ""


def _norm_title(title: str | None) -> str:
	return " ".join(str(title or "").strip().split()).casefold()


@dataclass
class BackfillCounters:
	songs_seen: int = 0
	songs_updated: int = 0
	features_created: int = 0
	artists_created: int = 0
	tracks_not_found: int = 0
	songs_skipped_no_spotify_id: int = 0


class Command(BaseCommand):
	help = "Backfill SongFeature rows for existing songs using Spotify track metadata."

	def add_arguments(self, parser):
		parser.add_argument(
			"--market",
			type=str,
			default="RO",
			help="Spotify market (default: RO)",
		)
		parser.add_argument(
			"--album-id",
			type=int,
			default=0,
			help="Only backfill songs from this album id",
		)
		parser.add_argument(
			"--song-id",
			type=int,
			default=0,
			help="Only backfill this specific song id",
		)
		parser.add_argument(
			"--artist-id",
			type=int,
			default=0,
			help="Only backfill songs that belong to this artist (matches Song.artist or Song.album.artist)",
		)
		parser.add_argument(
			"--artist-name",
			type=str,
			default="",
			help="Only backfill songs that belong to this artist name (case-insensitive; matches Song.artist or Song.album.artist)",
		)
		parser.add_argument(
			"--only-missing",
			action="store_true",
			help="Only process songs with no existing SongFeature rows",
		)
		parser.add_argument(
			"--max-songs",
			type=int,
			default=0,
			help="Stop after N songs (0 = no limit)",
		)
		parser.add_argument(
			"--approved",
			action="store_true",
			help="Mark newly created feature artists as approved",
		)
		parser.add_argument(
			"--with-artist-details",
			action="store_true",
			help="Fetch full artist details from Spotify (slower, but fills image/popularity/genres)",
		)
		parser.add_argument(
			"--max-rate-limit-wait-s",
			type=int,
			default=3600,
			help="Max seconds to wait on Spotify 429 before failing the command (default: 3600).",
		)
		parser.add_argument(
			"--dry-run",
			action="store_true",
			help="Don't write to DB; just print what would change",
		)
		parser.add_argument(
			"--sleep-ms",
			type=int,
			default=0,
			help="Sleep N milliseconds between Spotify API calls (helps avoid 429 rate limits)",
		)
		parser.add_argument(
			"--progress",
			action="store_true",
			help="Print progress while processing",
		)

	def handle(self, *args, **options):
		market: str = str(options.get("market") or "RO").strip() or "RO"
		album_id: int = int(options.get("album_id") or 0)
		song_id: int = int(options.get("song_id") or 0)
		artist_id: int = int(options.get("artist_id") or 0)
		artist_name: str = str(options.get("artist_name") or "").strip()
		only_missing: bool = bool(options.get("only_missing"))
		max_songs: int = int(options.get("max_songs") or 0)
		approved: bool = bool(options.get("approved"))
		with_artist_details: bool = bool(options.get("with_artist_details"))
		max_rate_limit_wait_s: int = int(options.get("max_rate_limit_wait_s") or 3600)
		dry_run: bool = bool(options.get("dry_run"))
		sleep_ms: int = int(options.get("sleep_ms") or 0)
		progress: bool = bool(options.get("progress"))
		sleep_s: float = max(0.0, min(float(sleep_ms) / 1000.0, 10.0))

		integration = MusicExternalIntegrationService()
		try:
			client = integration.spotify
		except SpotifyAuthError as e:
			raise CommandError(str(e))

		# Make rate-limiting behavior visible during long runs.
		client.verbose = bool(progress)
		client.max_rate_limit_wait_s = max(0, int(max_rate_limit_wait_s))

		if artist_name and artist_id > 0:
			raise CommandError("Use either --artist-id or --artist-name, not both.")

		if artist_name and artist_id <= 0:
			exact = list(Artist.objects.filter(name__iexact=artist_name).values_list("id", "name")[:5])
			if len(exact) == 1:
				artist_id = int(exact[0][0])
			elif len(exact) > 1:
				raise CommandError(
					"Multiple artists match that name exactly: "
					+ ", ".join([f"{aid}:{aname}" for aid, aname in exact])
					+ " (use --artist-id)"
				)
			else:
				partial = list(Artist.objects.filter(name__icontains=artist_name).values_list("id", "name")[:10])
				if len(partial) == 1:
					artist_id = int(partial[0][0])
				elif len(partial) == 0:
					raise CommandError(f"No artist found with name matching '{artist_name}'.")
				else:
					raise CommandError(
						"Multiple artists match that name: "
						+ ", ".join([f"{aid}:{aname}" for aid, aname in partial])
						+ " (use --artist-id)"
					)

		qs = Song.objects.select_related("artist", "album", "album__artist")
		if album_id > 0:
			qs = qs.filter(album_id=album_id)
		if song_id > 0:
			qs = qs.filter(id=song_id)
		if artist_id > 0:
			qs = qs.filter(Q(artist_id=artist_id) | Q(album__artist_id=artist_id))
		if only_missing:
			qs = qs.filter(features__isnull=True)

		# We can backfill feats in two ways:
		# - album tracks endpoint (requires album.spotify_id)
		# - track search endpoint (requires song.spotify_id / spotify_url)
		qs = qs.filter(
			(Q(album__spotify_id__isnull=False) & ~Q(album__spotify_id=""))
			| (Q(spotify_id__isnull=False) & ~Q(spotify_id=""))
			| ~Q(spotify_url="")
		)

		qs = qs.order_by("id")
		if max_songs > 0:
			qs = qs[:max_songs]

		if progress:
			self.stdout.write("Loading songs from DB...")
			self.stdout.flush()
		songs = list(qs)
		if progress:
			self.stdout.write(f"Loaded {len(songs)} songs.")
			self.stdout.flush()
		if not songs:
			self.stdout.write(self.style.WARNING("No songs matched filters."))
			return

		# Build mapping track_id -> song, plus a fallback map for album tracks
		# when a Song doesn't have spotify_id saved (match on track_number + title).
		track_id_to_song: dict[str, Song] = {}
		album_track_key_to_song: dict[tuple[str, int, str], Song] = {}
		for s in songs:
			track_id = _extract_spotify_track_id(spotify_id=s.spotify_id, spotify_url=s.spotify_url)
			if not track_id:
				track_id = ""
			else:
				track_id_to_song[track_id] = s

			album = getattr(s, "album", None)
			album_sid = str(getattr(album, "spotify_id", "") or "").strip()
			if album_sid:
				tn = int(getattr(s, "track_number", 0) or 0)
				norm = _norm_title(getattr(s, "title", ""))
				if tn > 0 and norm:
					album_track_key_to_song[(album_sid, tn, norm)] = s

		counters = BackfillCounters()
		artist_detail_cache: dict[str, dict[str, Any]] = {}

		track_ids = list(track_id_to_song.keys())

		def upsert_artist_from_track_artist(a: dict[str, Any]) -> tuple[Artist, bool]:
			spotify_artist_id = str(a.get("id") or "").strip()
			name = str(a.get("name") or "").strip() or "Unknown Artist"
			spotify_url = str((a.get("external_urls") or {}).get("spotify") or "").strip()

			defaults: dict[str, Any] = {
				"name": name,
				"slug": _unique_slug(Artist, f"{name}-{spotify_artist_id}"),
				"spotify_url": spotify_url,
				"is_approved": approved,
			}

			artist_obj, created = Artist.objects.get_or_create(
				spotify_id=spotify_artist_id,
				defaults=defaults,
			)

			# Light update if existing.
			dirty_fields: list[str] = []
			if not created:
				if name and artist_obj.name != name:
					artist_obj.name = name
					dirty_fields.append("name")
				if spotify_url and artist_obj.spotify_url != spotify_url:
					artist_obj.spotify_url = spotify_url
					dirty_fields.append("spotify_url")
				if approved and not artist_obj.is_approved:
					artist_obj.is_approved = True
					dirty_fields.append("is_approved")
				if dirty_fields and not dry_run:
					artist_obj.save(update_fields=dirty_fields)

			if with_artist_details:
				# Fill in richer details (optional) using /artists/{id}.
				if spotify_artist_id and spotify_artist_id not in artist_detail_cache:
					artist_detail_cache[spotify_artist_id] = client.get_artist(spotify_artist_id)
				full = artist_detail_cache.get(spotify_artist_id) or {}
				img = ""
				images = full.get("images") or []
				if images:
					img = str((images[0] or {}).get("url") or "").strip()
				pop = full.get("popularity")

				dirty2: list[str] = []
				if img and artist_obj.image_url != img:
					artist_obj.image_url = img
					dirty2.append("image_url")
				if pop is not None and artist_obj.popularity != pop:
					artist_obj.popularity = pop
					dirty2.append("popularity")
				if dirty2 and not dry_run:
					artist_obj.save(update_fields=dirty2)

			return artist_obj, created

		def _apply_features_for_song(*, song: Song, artists: list[dict[str, Any]]):
			if not artists:
				return

			song_primary_spotify_id = str(getattr(song.artist, "spotify_id", "") or "").strip()
			feature_candidates: list[dict[str, Any]] = []
			seen_ids: set[str] = set()
			for idx, a in enumerate(artists):
				a_id = str((a or {}).get("id") or "").strip()
				if not a_id:
					continue
				# If we don't know the primary artist spotify_id, skip the first artist to avoid
				# incorrectly creating a feature for the primary.
				if idx == 0 and not song_primary_spotify_id:
					continue
				if song_primary_spotify_id and a_id == song_primary_spotify_id:
					continue
				if a_id in seen_ids:
					continue
				seen_ids.add(a_id)
				feature_candidates.append(a)

			if not feature_candidates:
				return

			if dry_run:
				counters.songs_updated += 1
				counters.features_created += len(feature_candidates)
				return

			with transaction.atomic():
				created_any = False
				for a in feature_candidates:
					spotify_artist_id = str((a or {}).get("id") or "").strip()
					if not spotify_artist_id:
						continue

					try:
						artist_obj, artist_created = upsert_artist_from_track_artist(a)
					except SpotifyAPIError as e:
						raise CommandError(str(e))
					if artist_created:
						counters.artists_created += 1

					_, feat_created = SongFeature.objects.get_or_create(song=song, artist=artist_obj)
					if feat_created:
						counters.features_created += 1
						created_any = True

				if created_any:
					counters.songs_updated += 1

		processed_song_ids: set[int] = set()

		# 1) Prefer album-based backfill (fast, uses /albums/{id}/tracks).
		album_spotify_ids: set[str] = set()
		for s in songs:
			album = getattr(s, "album", None)
			album_sid = str(getattr(album, "spotify_id", "") or "").strip()
			if album_sid:
				album_spotify_ids.add(album_sid)

		album_sid_list = sorted(album_spotify_ids)
		for idx_album, album_sid in enumerate(album_sid_list, start=1):
			if progress:
				self.stdout.write(f"Album {idx_album}/{len(album_sid_list)}: {album_sid}")
				self.stdout.flush()
			offset = 0
			limit = 50
			while True:
				try:
					data = client.get_album_tracks(album_sid, market=market, limit=limit, offset=offset)
				except SpotifyAPIError as e:
					raise CommandError(str(e))
				if sleep_s:
					time.sleep(sleep_s)

				items = data.get("items") or []
				if not isinstance(items, list) or not items:
					break

				for track in items:
					track_id = str((track or {}).get("id") or "").strip()
					song = track_id_to_song.get(track_id) if track_id else None
					if not song:
						tn = int((track or {}).get("track_number") or 0)
						norm = _norm_title((track or {}).get("name"))
						if tn > 0 and norm:
							song = album_track_key_to_song.get((album_sid, tn, norm))
					if not song:
						continue

					processed_song_ids.add(int(song.id))
					counters.songs_seen += 1

					artists = (track or {}).get("artists") or []
					if not isinstance(artists, list) or not artists:
						continue
					_apply_features_for_song(song=song, artists=artists)

				offset += len(items)

		# 2) Fallback for singles / songs without album Spotify id (uses search).
		for song in songs:
			if int(song.id) in processed_song_ids:
				continue
			track_id = _extract_spotify_track_id(spotify_id=song.spotify_id, spotify_url=song.spotify_url)
			if not track_id:
				counters.songs_skipped_no_spotify_id += 1
				continue

			try:
				items = client.search_track(track_title=song.title, artist_name=song.artist.name, market=market, limit=5)
			except SpotifyAPIError as e:
				raise CommandError(str(e))
			if sleep_s:
				time.sleep(sleep_s)

			match: dict[str, Any] | None = None
			for it in items:
				if str((it or {}).get("id") or "").strip() == track_id:
					match = it
					break

			if not match:
				counters.tracks_not_found += 1
				continue

			counters.songs_seen += 1
			artists = (match or {}).get("artists") or []
			if not isinstance(artists, list) or not artists:
				continue
			_apply_features_for_song(song=song, artists=artists)

		summary = (
			f"Songs seen: {counters.songs_seen}; "
			f"Songs updated: {counters.songs_updated}; "
			f"Features created: {counters.features_created}; "
			f"Artists created: {counters.artists_created}; "
			f"Tracks not found: {counters.tracks_not_found}"
		)

		if dry_run:
			self.stdout.write(self.style.WARNING("DRY RUN - no DB changes written."))
		self.stdout.write(self.style.SUCCESS(summary))
