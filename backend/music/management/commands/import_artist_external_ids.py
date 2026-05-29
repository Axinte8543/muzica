from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from music.models import Artist
from music.musicbrainz import MusicBrainzClient, MusicBrainzAPIError
from music.spotify import SpotifyAPIError, SpotifyAuthError, SpotifyClient


def _normalize_name(value: str) -> str:
	return " ".join(str(value or "").strip().split())


def _norm_key(value: str) -> str:
	# Keep only alnum to make matching resilient to punctuation/diacritics.
	return re.sub(r"[^a-z0-9]+", "", _normalize_name(value).lower())


def _strip_parenthetical_notes(value: str) -> str:
	# E.g. "Cedry2k (dacă nu e deja)" -> "Cedry2k"
	v = str(value or "")
	v = re.sub(r"\s*\([^)]*\)\s*", " ", v)
	return _normalize_name(v)


def _unique_slug_for_artist(base: str) -> str:
	base_slug = slugify(_normalize_name(base)) or "artist"
	slug = base_slug
	suffix = 2
	while Artist.objects.filter(slug=slug).exists():
		slug = f"{base_slug}-{suffix}"
		suffix += 1
	return slug


_SPOTIFY_ARTIST_URL_RE = re.compile(r"open\.spotify\.com/artist/([A-Za-z0-9]+)")
_SPOTIFY_URI_RE = re.compile(r"spotify:artist:([A-Za-z0-9]+)")


def _extract_spotify_artist_id(url_or_uri: str) -> str:
	raw = str(url_or_uri or "").strip()
	if not raw:
		return ""
	m = _SPOTIFY_ARTIST_URL_RE.search(raw)
	if m:
		return m.group(1)
	m2 = _SPOTIFY_URI_RE.search(raw)
	if m2:
		return m2.group(1)
	return ""


@dataclass(frozen=True)
class Resolved:
	name: str
	musicbrainz_id: str = ""
	spotify_id: str = ""
	spotify_url: str = ""
	image_url: str = ""
	popularity: int | None = None
	aliases: list[str] | None = None


def _pick_image_url(images: list[dict[str, Any]] | None) -> str:
	images = images or []
	if not images:
		return ""
	return str(images[0].get("url") or "").strip()


def _mb_artist_is_romania(artist: dict[str, Any]) -> bool:
	area = artist.get("area") or {}
	name = str(area.get("name") or "").strip().lower()
	return name == "romania"


def _resolve_musicbrainz(*, mb: MusicBrainzClient, name: str, romanian_only: bool) -> Resolved:
	qname = str(name or "").strip()
	if not qname:
		return Resolved(name=name)

	# Prefer Romania when requested.
	query = f'artist:"{qname}"'
	if romanian_only:
		query = f'{query} AND area:Romania'

	payload = mb.search_artist(name=qname, query=query, limit=10)
	artists = payload.get("artists") or []
	if not isinstance(artists, list) or not artists:
		return Resolved(name=name)

	name_key = _norm_key(qname)

	def score(a: dict[str, Any]) -> tuple[int, int, int]:
		aname = _normalize_name(a.get("name") or "")
		exact = 1 if _norm_key(aname) == name_key else 0
		ro = 1 if _mb_artist_is_romania(a) else 0
		mb_score = int(a.get("score") or 0)
		return (exact, ro, mb_score)

	artists.sort(key=score, reverse=True)
	best = artists[0] if isinstance(artists[0], dict) else None
	if not best:
		return Resolved(name=name)

	mbid = _normalize_name(best.get("id") or "")
	if not mbid:
		return Resolved(name=name)

	# Fetch full artist with URL relations (for Spotify link) and aliases.
	full = mb.request(f"/artist/{mbid}", params={"inc": "url-rels+aliases"})
	relations = full.get("relations") or []
	spotify_url = ""
	spotify_id = ""
	if isinstance(relations, list):
		for rel in relations:
			if not isinstance(rel, dict):
				continue
			url_obj = rel.get("url")
			resource = ""
			if isinstance(url_obj, dict):
				resource = str(url_obj.get("resource") or "").strip()
			if not resource:
				continue
			if "open.spotify.com/artist/" in resource:
				spotify_url = resource
				spotify_id = _extract_spotify_artist_id(resource)
				break

	aliases_list: list[str] = []
	raw_aliases = full.get("aliases") or []
	if isinstance(raw_aliases, list):
		for a in raw_aliases:
			if not isinstance(a, dict):
				continue
			an = _normalize_name(a.get("name") or "")
			if not an:
				continue
			aliases_list.append(an)
	# De-dup + remove main name.
	seen = set()
	clean_aliases: list[str] = []
	for a in aliases_list:
		k = a.lower()
		if k in seen:
			continue
		seen.add(k)
		if _norm_key(a) == _norm_key(qname):
			continue
		clean_aliases.append(a)

	return Resolved(
		name=_normalize_name(full.get("name") or qname) or name,
		musicbrainz_id=mbid,
		spotify_id=spotify_id,
		spotify_url=spotify_url,
		aliases=clean_aliases,
	)


def _resolve_spotify(*, sp: SpotifyClient, name: str, limit: int, market: str) -> Resolved:
	qname = str(name or "").strip()
	if not qname:
		return Resolved(name=name)

	candidates = sp.search_artist(name=qname, market=market, limit=limit)
	if not candidates:
		return Resolved(name=name)

	name_key = _norm_key(qname)
	best: dict[str, Any] | None = None
	for c in candidates:
		cname = _normalize_name(c.get("name") or "")
		if _norm_key(cname) == name_key:
			best = c
			break
	if best is None:
		best = candidates[0]

	artist_id = _normalize_name(best.get("id") or "")
	artist_name = _normalize_name(best.get("name") or "") or qname
	artist_url = str((best.get("external_urls") or {}).get("spotify") or "").strip()
	artist_img = _pick_image_url(best.get("images"))
	pop = best.get("popularity")
	try:
		pop_int = int(pop) if pop is not None else None
	except Exception:
		pop_int = None

	return Resolved(
		name=artist_name,
		spotify_id=artist_id,
		spotify_url=artist_url,
		image_url=artist_img,
		popularity=pop_int,
	)


def _resolve_spotify_by_id(*, sp: SpotifyClient, spotify_id: str) -> Resolved:
	id = _normalize_name(spotify_id)
	if not id:
		return Resolved(name="")
	full = sp.get_artist(id)
	artist_name = _normalize_name(full.get("name") or "")
	artist_url = str((full.get("external_urls") or {}).get("spotify") or "").strip()
	artist_img = _pick_image_url(full.get("images"))
	pop = full.get("popularity")
	try:
		pop_int = int(pop) if pop is not None else None
	except Exception:
		pop_int = None
	return Resolved(
		name=artist_name,
		spotify_id=id,
		spotify_url=artist_url,
		image_url=artist_img,
		popularity=pop_int,
	)


class Command(BaseCommand):
	help = (
		"Resolve and attach MusicBrainz + Spotify external IDs to Artist rows (create missing artists optionally). "
		"This command is idempotent and safe to re-run."
	)

	def add_arguments(self, parser):
		parser.add_argument(
			"--artists",
			type=str,
			default="",
			help="Comma-separated list of artist names (notes in parentheses are stripped)",
		)
		parser.add_argument(
			"--artists-file",
			type=str,
			default="",
			help="Path to a UTF-8 text file with one artist name per line",
		)
		parser.add_argument(
			"--preset",
			type=str,
			default="",
			help="Use a built-in preset list (e.g. romanian-2026-04-17)",
		)
		parser.add_argument(
			"--create-missing",
			action="store_true",
			help="Create Artist rows when they do not exist",
		)
		parser.add_argument(
			"--approved",
			action="store_true",
			help="Mark affected artists as approved",
		)
		parser.add_argument(
			"--romanian",
			action="store_true",
			help="Mark affected artists as Romanian (is_romanian=true)",
		)
		parser.add_argument(
			"--romanian-only-mb",
			action="store_true",
			help="Prefer MusicBrainz matches with area:Romania",
		)
		parser.add_argument(
			"--market",
			type=str,
			default="RO",
			help="Spotify market (default RO)",
		)
		parser.add_argument(
			"--spotify-limit",
			type=int,
			default=5,
			help="Spotify search candidate limit (default 5)",
		)
		parser.add_argument(
			"--no-spotify",
			action="store_true",
			help="Skip Spotify lookups (still attaches Spotify URL if present in MusicBrainz url-rels)",
		)
		parser.add_argument(
			"--overwrite",
			action="store_true",
			help="Overwrite existing external IDs/URLs (default: only fill blanks)",
		)
		parser.add_argument(
			"--dry-run",
			action="store_true",
			help="Show what would change without writing to DB",
		)

	def handle(self, *args, **options):
		raw_artists = _normalize_name(options.get("artists") or "")
		artists_file = _normalize_name(options.get("artists_file") or "")
		preset = _normalize_name(options.get("preset") or "")
		create_missing = bool(options.get("create_missing"))
		approved = bool(options.get("approved"))
		romanian = bool(options.get("romanian"))
		romanian_only_mb = bool(options.get("romanian_only_mb"))
		market = _normalize_name(options.get("market") or "RO") or "RO"
		spotify_limit = max(1, min(int(options.get("spotify_limit") or 5), 20))
		no_spotify = bool(options.get("no_spotify"))
		overwrite = bool(options.get("overwrite"))
		dry_run = bool(options.get("dry_run"))

		names: list[str] = []
		if raw_artists:
			names.extend([_strip_parenthetical_notes(x) for x in raw_artists.split(",") if _strip_parenthetical_notes(x)])

		if artists_file:
			p = Path(artists_file)
			if not p.exists():
				raise CommandError(f"artists-file not found: {artists_file}")
			for line in p.read_text(encoding="utf-8").splitlines():
				line = _normalize_name(line)
				if not line or line.startswith("#"):
					continue
				names.append(_strip_parenthetical_notes(line))

		if preset:
			if preset != "romanian-2026-04-17":
				raise CommandError(f"Unknown preset: {preset}")
			preset_path = Path(__file__).resolve().parents[2] / "data" / "romanian_artists_2026-04-17.txt"
			if not preset_path.exists():
				raise CommandError(f"Preset file missing: {preset_path}")
			for line in preset_path.read_text(encoding="utf-8").splitlines():
				line = _normalize_name(line)
				if not line or line.startswith("#"):
					continue
				names.append(_strip_parenthetical_notes(line))

		# De-dup preserving order.
		seen: set[str] = set()
		clean_names: list[str] = []
		for n in names:
			k = n.lower()
			if not n or k in seen:
				continue
			seen.add(k)
			clean_names.append(n)

		if not clean_names:
			raise CommandError("Provide --artists, --artists-file, or --preset")

		mb = MusicBrainzClient()

		sp: SpotifyClient | None = None
		if not no_spotify:
			try:
				sp = SpotifyClient()
			except SpotifyAuthError as e:
				self.stdout.write(self.style.WARNING(f"Spotify disabled: {e}"))
				sp = None

		created = 0
		updated = 0
		skipped = 0

		for raw_name in clean_names:
			name = _normalize_name(raw_name)
			if not name:
				continue

			self.stdout.write(self.style.MIGRATE_HEADING(f"Resolve: {name}"))

			mb_res = Resolved(name=name)
			try:
				mb_res = _resolve_musicbrainz(mb=mb, name=name, romanian_only=romanian_only_mb)
			except MusicBrainzAPIError as e:
				self.stdout.write(self.style.WARNING(f"MusicBrainz error for {name}: {e}"))

			sp_res = Resolved(name=name)
			if sp is not None:
				try:
					mb_spotify_id = mb_res.spotify_id or _extract_spotify_artist_id(mb_res.spotify_url)
					if mb_spotify_id:
						sp_res = _resolve_spotify_by_id(sp=sp, spotify_id=mb_spotify_id)
					else:
						sp_res = _resolve_spotify(sp=sp, name=name, limit=spotify_limit, market=market)
				except SpotifyAPIError as e:
					self.stdout.write(self.style.WARNING(f"Spotify error for {name}: {e}"))

			# Merge best-known fields.
			final_name = mb_res.name or sp_res.name or name
			musicbrainz_id = mb_res.musicbrainz_id
			spotify_id = sp_res.spotify_id or mb_res.spotify_id
			spotify_url = sp_res.spotify_url or mb_res.spotify_url
			image_url = sp_res.image_url
			popularity = sp_res.popularity
			aliases = mb_res.aliases or []

			# Find an existing artist row.
			artist = None
			if musicbrainz_id:
				artist = Artist.objects.filter(musicbrainz_id=musicbrainz_id).first()
			if artist is None and spotify_id:
				artist = Artist.objects.filter(spotify_id=spotify_id).first()
			if artist is None:
				artist = Artist.objects.filter(name__iexact=name).first()

			if artist is None and not create_missing:
				self.stdout.write(self.style.WARNING(f"Skip (missing, create disabled): {name}"))
				skipped += 1
				continue

			if artist is None:
				if dry_run:
					self.stdout.write(self.style.WARNING(f"[dry-run] create Artist: {final_name}"))
					created += 1
					continue
				with transaction.atomic():
					artist = Artist(
						name=final_name,
						slug=_unique_slug_for_artist(final_name),
						musicbrainz_id=musicbrainz_id or None,
						spotify_id=spotify_id or None,
						spotify_url=spotify_url,
						image_url=image_url,
						popularity=popularity,
						aliases=", ".join(aliases),
						is_romanian=romanian,
						is_approved=approved,
					)
					artist.save()
				created += 1
				continue

			# Update existing artist.
			dirty: list[str] = []
			# Prefer stylized/correct name only when it's basically the same artist.
			if final_name and _norm_key(final_name) == _norm_key(artist.name) and artist.name != final_name:
				artist.name = final_name
				dirty.append("name")

			if musicbrainz_id and (overwrite or not artist.musicbrainz_id):
				# Avoid accidental collisions.
				conflict = Artist.objects.filter(musicbrainz_id=musicbrainz_id).exclude(pk=artist.pk).only("id", "name").first()
				if conflict is None:
					artist.musicbrainz_id = musicbrainz_id
					dirty.append("musicbrainz_id")

			if spotify_id and (overwrite or not artist.spotify_id):
				conflict = Artist.objects.filter(spotify_id=spotify_id).exclude(pk=artist.pk).only("id", "name").first()
				if conflict is None:
					artist.spotify_id = spotify_id
					dirty.append("spotify_id")

			if spotify_url and (overwrite or not (artist.spotify_url or "").strip()):
				artist.spotify_url = spotify_url
				dirty.append("spotify_url")

			if image_url and (overwrite or not (artist.image_url or "").strip()):
				artist.image_url = image_url
				dirty.append("image_url")

			if popularity is not None and (overwrite or artist.popularity is None):
				artist.popularity = popularity
				dirty.append("popularity")

			if aliases and (overwrite or not (artist.aliases or "").strip()):
				artist.aliases = ", ".join(aliases)
				dirty.append("aliases")

			if romanian and not artist.is_romanian:
				artist.is_romanian = True
				dirty.append("is_romanian")

			if approved and not artist.is_approved:
				artist.is_approved = True
				dirty.append("is_approved")

			if not dirty:
				self.stdout.write(self.style.SUCCESS(f"OK (unchanged): {artist.name}"))
				continue

			if dry_run:
				self.stdout.write(self.style.WARNING(f"[dry-run] update Artist: {artist.name} ({', '.join(dirty)})"))
				updated += 1
				continue

			with transaction.atomic():
				artist.save(update_fields=list(dict.fromkeys(dirty)))
			updated += 1

		self.stdout.write(self.style.SUCCESS(f"Done. created={created}, updated={updated}, skipped={skipped}"))
