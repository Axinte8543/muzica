from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from interactions.models import ArtistFollow, UserActivity
from music.models import Album, Artist, ArtistSimilarity, Song


@dataclass(frozen=True)
class MergeStats:
	albums_moved: int
	songs_moved: int
	follows_moved: int
	follows_deleted_dupes: int
	sim_edges_from_moved: int
	sim_edges_to_moved: int
	sim_edges_merged: int
	activities_updated: int


class Command(BaseCommand):
	help = "Merge a source Artist into a target Artist (repoint albums/songs/follows/similarity)."

	def add_arguments(self, parser):
                          
		parser.add_argument('--source-id', type=int)
		parser.add_argument('--target-id', type=int)
		parser.add_argument('--source-name', type=str)
		parser.add_argument('--target-name', type=str)

                  
		parser.add_argument('--strip-names', action='store_true', help='Strip whitespace from artist names')
		parser.add_argument('--force', action='store_true', help='Allow conflicting IDs (Spotify/MBID) to be overwritten')
		parser.add_argument('--yes', action='store_true', help='Apply changes (otherwise dry-run)')

	def handle(self, *args, **options):
		source = self._resolve_artist(options.get('source_id'), options.get('source_name'), label='source')
		target = self._resolve_artist(options.get('target_id'), options.get('target_name'), label='target')

		if source.id == target.id:
			raise CommandError('Source and target must be different artists.')

		self.stdout.write(self.style.NOTICE(f"Source: {source.id} '{source.name}' (spotify_id={source.spotify_id}, mbid={source.musicbrainz_id})"))
		self.stdout.write(self.style.NOTICE(f"Target: {target.id} '{target.name}' (spotify_id={target.spotify_id}, mbid={target.musicbrainz_id})"))

		stats_preview = self._compute_preview_stats(source, target)
		self.stdout.write(self.style.NOTICE('Preview:'))
		self._print_stats(stats_preview)

		if not options.get('yes'):
			self.stdout.write(self.style.WARNING('Dry-run only. Re-run with --yes to apply.'))
			return

		with transaction.atomic():
			stats = self._merge(source, target, strip_names=options.get('strip_names', False), force=options.get('force', False))

		self.stdout.write(self.style.SUCCESS('Merged successfully.'))
		self._print_stats(stats)

	def _resolve_artist(self, artist_id: int | None, artist_name: str | None, *, label: str) -> Artist:
		if artist_id is None and not artist_name:
			raise CommandError(f"Must provide --{label}-id or --{label}-name")

		qs = Artist.objects.all()
		if artist_id is not None:
			try:
				return qs.get(id=artist_id)
			except Artist.DoesNotExist as exc:
				raise CommandError(f"No artist found for --{label}-id={artist_id}") from exc

		matches = list(qs.filter(name__iexact=artist_name))
		if not matches:
			raise CommandError(f"No artist found for --{label}-name='{artist_name}'")
		if len(matches) > 1:
			raise CommandError(f"Multiple artists match --{label}-name='{artist_name}': {[a.id for a in matches]}")
		return matches[0]

	def _compute_preview_stats(self, source: Artist, target: Artist) -> MergeStats:
		albums_moved = Album.objects.filter(artist=source).count()
		songs_moved = Song.objects.filter(artist=source).count()
		follows_moved = ArtistFollow.objects.filter(artist=source).count()
		follows_deleted_dupes = ArtistFollow.objects.filter(
		 artist=source,
		 user_id__in=ArtistFollow.objects.filter(artist=target).values_list('user_id', flat=True),
		).count()

		sim_edges_from_moved = ArtistSimilarity.objects.filter(from_artist=source).count()
		sim_edges_to_moved = ArtistSimilarity.objects.filter(to_artist=source).count()

                                              
		sim_edges_merged = 0
		activities_updated = UserActivity.objects.filter(
		 activity_type=UserActivity.Type.FOLLOW_ARTIST,
		 target_id=source.id,
		).count()

		return MergeStats(
		 albums_moved=albums_moved,
		 songs_moved=songs_moved,
		 follows_moved=follows_moved,
		 follows_deleted_dupes=follows_deleted_dupes,
		 sim_edges_from_moved=sim_edges_from_moved,
		 sim_edges_to_moved=sim_edges_to_moved,
		 sim_edges_merged=sim_edges_merged,
		 activities_updated=activities_updated,
		)

	def _print_stats(self, stats: MergeStats) -> None:
		self.stdout.write(
		 "  "
		 + ", ".join(
		  [
		   f"albums_moved={stats.albums_moved}",
		   f"songs_moved={stats.songs_moved}",
		   f"follows_moved={stats.follows_moved}",
		   f"follows_deleted_dupes={stats.follows_deleted_dupes}",
		   f"sim_edges_from_moved={stats.sim_edges_from_moved}",
		   f"sim_edges_to_moved={stats.sim_edges_to_moved}",
		   f"sim_edges_merged={stats.sim_edges_merged}",
		   f"activities_updated={stats.activities_updated}",
		  ]
		 )
		)

	def _merge(self, source: Artist, target: Artist, *, strip_names: bool, force: bool) -> MergeStats:
                       
		if strip_names:
			source_name = source.name.strip()
			target_name = target.name.strip()
			if source_name != source.name:
				source.name = source_name
				source.save(update_fields=['name'])
			if target_name != target.name:
				target.name = target_name
				target.save(update_fields=['name'])

                                        
		target = Artist.objects.select_for_update().get(id=target.id)
		source = Artist.objects.select_for_update().get(id=source.id)

		for field in ['spotify_id', 'musicbrainz_id']:
			s_val = getattr(source, field)
			t_val = getattr(target, field)
			if s_val and t_val and s_val != t_val:
				if not force:
					raise CommandError(f"Conflicting {field}: source={s_val} target={t_val}. Use --force to override.")
                                             
			elif s_val and not t_val:
                                                                                      
				setattr(source, field, None)
				source.save(update_fields=[field])
				setattr(target, field, s_val)

                                
		if not target.spotify_url and source.spotify_url:
			target.spotify_url = source.spotify_url
		if not target.image_url and source.image_url:
			target.image_url = source.image_url
		if target.popularity is None and source.popularity is not None:
			target.popularity = source.popularity
		if not target.bio and source.bio:
			target.bio = source.bio
		target.is_approved = bool(target.is_approved or source.is_approved)
		target.is_romanian = bool(target.is_romanian or source.is_romanian)

                                                                 
		aliases = self._split_csv(target.aliases) | self._split_csv(source.aliases)
		source_name_alias = str(source.name or '').strip()
		target_name_alias = str(target.name or '').strip()
		if source_name_alias and target_name_alias and source_name_alias.lower() != target_name_alias.lower():
			aliases.add(source_name_alias)
		target.aliases = ", ".join(sorted(a for a in aliases if a))

		target.save()

                 
		if source.genres.exists():
			target.genres.add(*source.genres.all())

		albums_moved = Album.objects.filter(artist=source).update(artist=target)
		songs_moved = Song.objects.filter(artist=source).update(artist=target)

                                                      
		dupe_follow_qs = ArtistFollow.objects.filter(
		 artist=source,
		 user_id__in=ArtistFollow.objects.filter(artist=target).values_list('user_id', flat=True),
		)
		follows_deleted_dupes = dupe_follow_qs.count()
		dupe_follow_qs.delete()
		follows_moved = ArtistFollow.objects.filter(artist=source).update(artist=target)

                                                                 
		sim_edges_merged = 0
                         
		for edge in list(ArtistSimilarity.objects.filter(from_artist=source)):
			existing = ArtistSimilarity.objects.filter(from_artist=target, to_artist=edge.to_artist, source=edge.source).first()
			if existing:
				if edge.match is not None:
					existing.match = max(existing.match or 0.0, edge.match)
					existing.save(update_fields=['match'])
				edge.delete()
				sim_edges_merged += 1
                       
		for edge in list(ArtistSimilarity.objects.filter(to_artist=source)):
			existing = ArtistSimilarity.objects.filter(from_artist=edge.from_artist, to_artist=target, source=edge.source).first()
			if existing:
				if edge.match is not None:
					existing.match = max(existing.match or 0.0, edge.match)
					existing.save(update_fields=['match'])
				edge.delete()
				sim_edges_merged += 1

		sim_edges_from_moved = ArtistSimilarity.objects.filter(from_artist=source).update(from_artist=target)
		sim_edges_to_moved = ArtistSimilarity.objects.filter(to_artist=source).update(to_artist=target)

                                                          
		activities_updated = UserActivity.objects.filter(
		 activity_type=UserActivity.Type.FOLLOW_ARTIST,
		 target_id=source.id,
		).update(target_id=target.id, target_name=target.name)

                 
		source.delete()

		return MergeStats(
		 albums_moved=albums_moved,
		 songs_moved=songs_moved,
		 follows_moved=follows_moved,
		 follows_deleted_dupes=follows_deleted_dupes,
		 sim_edges_from_moved=sim_edges_from_moved,
		 sim_edges_to_moved=sim_edges_to_moved,
		 sim_edges_merged=sim_edges_merged,
		 activities_updated=activities_updated,
		)

	def _split_csv(self, value: str) -> set[str]:
		if not value:
			return set()
		return {part.strip() for part in value.split(',') if part.strip()}
