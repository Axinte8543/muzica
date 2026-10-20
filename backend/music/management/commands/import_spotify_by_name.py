from __future__ import annotations

import re

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from music.models import Artist
from music.spotify import SpotifyAPIError, SpotifyAuthError, SpotifyClient


def _normalize_name(value: str) -> str:
	return " ".join(str(value or "").strip().split())


def _norm_key(value: str) -> str:
                                                                  
	return re.sub(r"[^a-z0-9]+", "", _normalize_name(value).lower())


class Command(BaseCommand):
	help = "Search Spotify artists by name and import discography for the best match (wraps import_spotify_artists)."

	def add_arguments(self, parser):
		parser.add_argument(
		 "--artists",
		 type=str,
		 default="",
		 help="Comma-separated list of artist names",
		)
		parser.add_argument(
		 "--artists-file",
		 type=str,
		 default="",
		 help="Path to a UTF-8 text file with one artist name per line",
		)
		parser.add_argument(
		 "--limit",
		 type=int,
		 default=5,
		 help="How many Spotify search candidates to consider (default: 5)",
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
		parser.add_argument(
		 "--strict",
		 action="store_true",
		 help="Require an exact (normalized) name match; otherwise skip the artist",
		)
		parser.add_argument(
		 "--list-only",
		 action="store_true",
		 help="Only list Spotify search candidates; do not import anything",
		)
		parser.add_argument(
		 "--all-existing",
		 action="store_true",
		 help="Process all artists currently present in the local database",
		)

	def handle(self, *args, **options):
		raw_artists = _normalize_name(options.get("artists") or "")
		artists_file = _normalize_name(options.get("artists_file") or "")
		market = _normalize_name(options.get("market") or "RO") or "RO"
		include_groups = _normalize_name(options.get("include_groups") or "album,single") or "album,single"
		max_albums = int(options.get("max_albums") or 0)
		approved = bool(options.get("approved"))
		strict = bool(options.get("strict"))
		limit = max(1, min(int(options.get("limit") or 5), 20))
		list_only = bool(options.get("list_only"))
		all_existing = bool(options.get("all_existing"))

		names: list[str] = []
		if all_existing:
			names.extend(
			 Artist.objects.order_by("name", "id").values_list("name", flat=True)
			)
		if raw_artists:
			names.extend([_normalize_name(x) for x in raw_artists.split(",") if _normalize_name(x)])
		if artists_file:
			try:
				with open(artists_file, "r", encoding="utf-8") as f:
					for line in f:
						n = _normalize_name(line)
						if n and not n.startswith("#"):
							names.append(n)
			except FileNotFoundError:
				raise CommandError(f"artists-file not found: {artists_file}")

                           
		seen: set[str] = set()
		clean_names: list[str] = []
		for n in names:
			key = n.lower()
			if key in seen:
				continue
			seen.add(key)
			clean_names.append(n)

		if not clean_names:
			raise CommandError("Provide --artists or --artists-file")

		try:
			client = SpotifyClient()
		except SpotifyAuthError as e:
			raise CommandError(str(e))

		resolved_ids: list[str] = []
		for name in clean_names:
			try:
				candidates = client.search_artist(name=name, market=market, limit=limit)
			except SpotifyAPIError as exc:
				self.stdout.write(self.style.WARNING(f"Spotify stopped while searching {name}: {exc}"))
				break
			if not candidates:
				self.stdout.write(self.style.WARNING(f"Spotify: no match for {name}"))
				continue

			if list_only:
				self.stdout.write(self.style.MIGRATE_HEADING(f"Spotify candidates for: {name}"))
				for idx, c in enumerate(candidates, start=1):
					c_name = _normalize_name(c.get("name") or "")
					c_id = _normalize_name(c.get("id") or "")
					pop = c.get("popularity")
					followers = ((c.get("followers") or {}).get("total")) if isinstance(c.get("followers"), dict) else None
					genres = c.get("genres") if isinstance(c.get("genres"), list) else []
					genres_s = ", ".join([str(g) for g in genres[:5]])
					self.stdout.write(f"  {idx}) {c_name} | id={c_id} | popularity={pop} | followers={followers} | genres={genres_s}")
				continue

			name_key = _norm_key(name)
			best = None
			for c in candidates:
				c_name = _normalize_name(c.get("name") or "")
				if _norm_key(c_name) == name_key:
					best = c
					break
			if best is None:
				if strict:
					self.stdout.write(self.style.WARNING(f"Spotify: skipping {name} (no exact match in top results)"))
					continue
				best = candidates[0]

			artist_id = _normalize_name(best.get("id") or "")
			artist_name = _normalize_name(best.get("name") or "") or name
			if not artist_id:
				self.stdout.write(self.style.WARNING(f"Spotify: invalid artist id for {name}"))
				continue

                                                                                        
                                                                                          
			existing = Artist.objects.filter(name__iexact=name).first()
			if existing is not None:
				other = Artist.objects.filter(spotify_id=artist_id).exclude(pk=existing.pk).only("id", "name").first()
				if other is not None:
					self.stdout.write(
					 self.style.WARNING(
					  f"Spotify: ID {artist_id} already attached to {other.name}; skipping pre-attach for {name}."
					 )
					)
				else:
					dirty = []
					if not existing.spotify_id:
						existing.spotify_id = artist_id
						dirty.append("spotify_id")
					if approved and not existing.is_approved:
						existing.is_approved = True
						dirty.append("is_approved")
					if dirty:
						existing.save(update_fields=dirty)

			self.stdout.write(self.style.MIGRATE_HEADING(f"Spotify resolved: {name} -> {artist_name} ({artist_id})"))
			if list_only:
				resolved_ids.append(artist_id)
				continue

			try:
				call_command(
				 "import_spotify_artists",
				 artist_id,
				 market=market,
				 include_groups=include_groups,
				 max_albums=max_albums,
				 approved=approved,
				 verbosity=1,
				)
			except CommandError as exc:
				self.stdout.write(self.style.WARNING(f"Spotify import failed for {name}: {exc}"))
				if "429" in str(exc) or "rate limit" in str(exc).lower():
					break

		if list_only:
			self.stdout.write(self.style.SUCCESS("Listed Spotify candidates only; nothing imported."))
			return
