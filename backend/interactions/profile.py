from django.db.models import Avg, Count, Q

from interactions.models import AlbumListen, AlbumRating, AlbumReview, ArtistFollow, FavoriteAlbum, FavoriteSong, List, MetadataSuggestion


def favorite_albums_payload_for(user) -> list[dict]:
	qs = (
	 FavoriteAlbum.objects.select_related('album', 'album__artist')
	 .filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	 )
	 .order_by('position', 'id')
	)
	by_pos = {int(f.position): f for f in qs}
	items: list[dict] = []
	for pos in (1, 2, 3, 4):
		f = by_pos.get(pos)
		if not f:
			items.append(
			 {
			  "position": pos,
			  "album_id": None,
			  "album_title": None,
			  "album_slug": None,
			  "artist_name": None,
			  "artist_slug": None,
			  "cover_url": None,
			 }
			)
			continue

		album = f.album
		items.append(
		 {
		  "position": pos,
		  "album_id": int(album.id),
		  "album_title": album.title,
		  "album_slug": album.slug,
		  "artist_name": album.artist.name,
		  "artist_slug": album.artist.slug,
		  "cover_url": album.cover_url,
		 }
		)

	return items


def favorite_songs_payload_for(user) -> list[dict]:
	qs = (
	 FavoriteSong.objects.select_related('song', 'song__artist', 'song__album', 'song__album__artist')
	 .filter(
	  user=user,
	  song__is_approved=True,
	  song__artist__is_approved=True,
	 )
	 .filter(Q(song__album__isnull=True) | Q(song__album__is_approved=True, song__album__artist__is_approved=True))
	 .order_by('position', 'id')
	)
	by_pos = {int(f.position): f for f in qs}
	items: list[dict] = []
	for pos in (1, 2, 3, 4):
		f = by_pos.get(pos)
		if not f:
			items.append(
			 {
			  "position": pos,
			  "song_id": None,
			  "song_title": None,
			  "song_slug": None,
			  "artist_name": None,
			  "artist_slug": None,
			  "album_title": None,
			  "album_slug": None,
			 }
			)
			continue

		song = f.song
		album = song.album
		items.append(
		 {
		  "position": pos,
		  "song_id": int(song.id),
		  "song_title": song.title,
		  "song_slug": song.slug,
		  "artist_name": song.artist.name,
		  "artist_slug": song.artist.slug,
		  "album_title": album.title if album else None,
		  "album_slug": album.slug if album else None,
		 }
		)

	return items


def profile_stats_payload_for(user) -> dict:
	qs = (
	 AlbumRating.objects.select_related('album', 'album__artist')
	 .prefetch_related('album__genres')
	 .filter(
	  user=user,
	  album__is_approved=True,
	  album__artist__is_approved=True,
	 )
	)

	agg = qs.aggregate(total=Count('id'), avg=Avg('rating'))
	total = int(agg.get('total') or 0)
	avg = agg.get('avg')
	avg_out = round(float(avg), 2) if avg is not None else None

	rating_rows = qs.values('rating').annotate(c=Count('id'))
	ratings_by_value = {int(r['rating']): int(r['c'] or 0) for r in rating_rows if r.get('rating')}
	ratings_distribution = [
	 {"stars": stars, "count": int(ratings_by_value.get(stars, 0))}
	 for stars in range(5, 0, -1)
	]

	genre_rows = (
	 qs.filter(album__genres__isnull=False)
	 .values('album__genres__name')
	 .annotate(ratings=Count('id'))
	 .order_by('-ratings', 'album__genres__name')
	)
	top_genres_rated = [
	 {"name": row['album__genres__name'], "ratings": int(row['ratings'] or 0)}
	 for row in genre_rows[:10]
	 if row.get('album__genres__name')
	]

	reviews_written = AlbumReview.objects.filter(
	 user=user,
	 album__is_approved=True,
	 album__artist__is_approved=True,
	).count()
	artists_followed = ArtistFollow.objects.filter(
	 user=user,
	 artist__is_approved=True,
	).count()
	approved_suggestions = MetadataSuggestion.objects.filter(
	 suggester=user,
	 status=MetadataSuggestion.Status.APPROVED,
	).count()
	lists_created = List.objects.filter(user=user).count()
	activity = {
	 "reviews_written": int(reviews_written),
	 "albums_rated": int(total),
	 "artists_followed": int(artists_followed),
	 "lists_created": int(lists_created),
	}

                                    
                                                                                   
	distinct_genres_rated = (
	 qs.filter(album__genres__isnull=False)
	 .values('album__genres__id')
	 .distinct()
	 .count()
	)

                                                  
	release_dates = list(qs.values_list('album__release_date', flat=True))
	decades = set()
	for d in release_dates:
		if not d:
			continue
		try:
			y = int(getattr(d, 'year', None))
		except Exception:
			continue
		if y:
			decades.add((y // 10) * 10)

	listens_qs = AlbumListen.objects.select_related('album', 'album__artist').filter(
	 user=user,
	 album__is_approved=True,
	 album__artist__is_approved=True,
	)
	artists_listened = (
	 listens_qs
	 .values('album__artist_id')
	 .distinct()
	 .count()
	)

	badges = [
	 {
	  "key": "first_review",
	  "title": "Primul review",
	  "description": "Scrie 1 review",
	  "unlocked": int(reviews_written) >= 1,
	 },
	 {
	  "key": "critic_10",
	  "title": "Critic",
	  "description": "Scrie 10 review-uri",
	  "unlocked": int(reviews_written) >= 10,
	 },
	 {
	  "key": "rater_10",
	  "title": "În formă",
	  "description": "Evaluează 10 albume",
	  "unlocked": int(total) >= 10,
	 },
	 {
	  "key": "rater_50",
	  "title": "Consecvent",
	  "description": "Evaluează 50 de albume",
	  "unlocked": int(total) >= 50,
	 },
	 {
	  "key": "curator_3",
	  "title": "Curator",
	  "description": "Creează 3 liste",
	  "unlocked": int(lists_created) >= 3,
	 },
	 {
	  "key": "fan_5",
	  "title": "Fan",
	  "description": "Urmărește 5 artiști",
	  "unlocked": int(artists_followed) >= 5,
	 },
	 {
	  "key": "contributor_5",
	  "title": "Contributor",
	  "description": "Ai 5 sugestii aprobate",
	  "unlocked": int(approved_suggestions) >= 5,
	 },
	 {
	  "key": "genre_explorer_5",
	  "title": "Explorator de genuri",
	  "description": "Evaluează albume din 5 genuri diferite",
	  "unlocked": int(distinct_genres_rated) >= 5,
	 },
	 {
	  "key": "decade_explorer_4",
	  "title": "Călător în timp",
	  "description": "Evaluează albume din 4 decade diferite",
	  "unlocked": len(decades) >= 4,
	 },
	 {
	  "key": "romanian_mix",
	  "title": "Mix românesc",
	  "description": "Ascultă 3 artiști diferiți",
	  "unlocked": int(artists_listened) >= 3,
	 },
	]

	genre_row = (
	 qs.values('album__genres__name')
	 .annotate(c=Count('id'))
	 .order_by('-c', 'album__genres__name')
	 .first()
	)
	favorite_genre = genre_row.get('album__genres__name') if genre_row else None

	artist_row = (
	 qs.values('album__artist__name')
	 .annotate(c=Count('id'))
	 .order_by('-c', 'album__artist__name')
	 .first()
	)
	favorite_artist = artist_row.get('album__artist__name') if artist_row else None

	return {
	 "favorite_albums": favorite_albums_payload_for(user),
	 "favorite_songs": favorite_songs_payload_for(user),
	 "favorite_genre": favorite_genre,
	 "favorite_artist": favorite_artist,
	 "total_ratings": total,
	 "average_rating_given": avg_out,
	 "ratings_distribution": ratings_distribution,
	 "top_genres_rated": top_genres_rated,
	 "activity": activity,
	 "badges": badges,
	}
