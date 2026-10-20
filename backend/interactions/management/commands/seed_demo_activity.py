from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify

from interactions.achievement_tracker import update_all_achievement_progress
from interactions.models import (
    Achievement,
	AchievementUnlock,
	AlbumLike,
	AlbumListen,
	AlbumRating,
    AlbumReview,
    AlbumReviewLike,
    ArtistFollow,
    Badge,
    FavoriteAlbum,
    FavoriteSong,
    FriendRequest,
    List,
    ListAlbum,
    ListLike,
    ReviewComment,
    SongLike,
    SongRating,
    UserAchievement,
    UserActivity,
    UserBadge,
    UserXP,
)
from music.models import Album, Artist, Genre, Song
from users.models import UserPrivacySettings


User = get_user_model()


DEMO_USERS = [
    ("alexandru.popa", "alexandru.popa@example.com"),
    ("mara.ionescu", "mara.ionescu@example.com"),
    ("ionut.stan", "ionut.stan@example.com"),
    ("irina.dumitru", "irina.dumitru@example.com"),
    ("vlad.georgescu", "vlad.georgescu@example.com"),
    ("teodora.marin", "teodora.marin@example.com"),
]

REVIEW_TEXTS = [
    (
        "Un album care crește cu fiecare ascultare",
        "Producția este atent construită, iar piesele se leagă natural. După câteva ascultări am descoperit mai multe detalii decât la prima trecere.",
    ),
    (
        "Atmosferă bine conturată",
        "Albumul păstrează aceeași atmosferă de la început până la final, fără să devină monoton. Câteva refrene mi-au rămas imediat în minte.",
    ),
    (
        "Câteva piese care rămân",
        "Nu toate momentele au aceeași forță, dar piesele cele mai bune compensează. Mi-au plăcut energia și atenția acordată detaliilor sonore.",
    ),
    (
        "O direcție muzicală convingătoare",
        "Se simte o identitate clară și o evoluție față de materialele anterioare. Ordinea pieselor face albumul ușor de ascultat cap-coadă.",
    ),
    (
        "Idei bune și un sunet coerent",
        "Instrumentalul și vocea se completează bine, iar schimbările de ritm mențin interesul. Este un material la care aș reveni.",
    ),
    (
        "O surpriză plăcută",
        "Am pornit fără așteptări foarte mari, dar albumul m-a convins prin varietate și prin modul în care își construiește momentele importante.",
    ),
]

COMMENT_TEXTS = [
    "Și mie mi-a atras atenția producția, mai ales în a doua jumătate a albumului.",
    "Sunt de acord cu observația despre atmosferă; albumul funcționează cel mai bine ascultat integral.",
    "Pentru mine, piesa de deschidere a stabilit foarte bine direcția întregului material.",
    "După a doua ascultare mi-au plăcut mai mult piesele pe care inițial le trecusem cu vederea.",
    "Aș adăuga că versurile sunt unul dintre punctele forte ale albumului.",
    "Interesantă perspectiva. Eu am apreciat în special ritmul și tranzițiile dintre piese.",
]


BADGES = [
    ("first_rating", "Prima nota", "Ai evaluat primul album.", "milestone", "common"),
    ("ten_ratings", "Radar muzical", "Ai evaluat 10 albume.", "milestone", "common"),
    ("fifty_ratings", "Arhivar de gusturi", "Ai evaluat 50 de albume.", "milestone", "rare"),
    ("first_review", "Primul review", "Ai scris primul review.", "critic", "common"),
    ("review_club", "Clubul criticilor", "Ai scris 5 review-uri.", "critic", "uncommon"),
    ("list_maker", "List maker", "Ai creat prima lista.", "collector", "common"),
    ("curator_plus", "Curator plus", "Ai creat 3 liste.", "collector", "uncommon"),
    ("social_start", "Social start", "Ai primul prieten.", "social", "common"),
    ("social_circle", "Cerc muzical", "Ai 3 prieteni.", "social", "uncommon"),
    ("artist_fan", "Fan dedicat", "Urmaresti 5 artisti.", "explorer", "common"),
    ("song_rater", "Ureche fina", "Ai evaluat 10 piese.", "activity", "uncommon"),
    ("weekly_active", "Saptamana activa", "Ai activitate muzicala in saptamana curenta.", "activity", "common"),
]


ACHIEVEMENTS = [
    ("list_architect", "List Architect", "Adauga 20 de albume in liste.", "milestone", 20, 35),
    ("social_listener", "Social Listener", "Fa 3 prieteni pe platforma.", "social", 3, 30),
    ("song_scout", "Song Scout", "Evalueaza 20 de piese.", "discovery", 20, 30),
    ("review_conversation", "Review Conversation", "Primeste sau lasa 5 comentarii la review-uri.", "social", 5, 25),
    ("release_hunter", "Release Hunter", "Asculta 5 release-uri noi.", "discovery", 5, 25),
]


def _set_created_at(obj, when):
    obj.__class__.objects.filter(pk=obj.pk).update(created_at=when)


def _set_activity_at(obj, when):
    obj.__class__.objects.filter(pk=obj.pk).update(created_at=when)


def _rating_value(index: int) -> int:
    return [5, 4, 4, 3, 5, 2, 4, 5][index % 8]


class Command(BaseCommand):
    help = "Seed realistic demo social activity: users, ratings, lists, friends, recent releases and gamification."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=6)
        parser.add_argument("--ratings-per-user", type=int, default=28)
        parser.add_argument("--reviews-per-user", type=int, default=4)
        parser.add_argument("--lists-per-user", type=int, default=3)
        parser.add_argument("--recent-releases", type=int, default=8)
        parser.add_argument("--seed", type=int, default=20260602)
        parser.add_argument(
            "--include-user",
            action="append",
            default=[],
            help="Existing username to include in the seeded activity. Can be passed multiple times.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(int(options["seed"]))
        today = timezone.localdate()
        now = timezone.now()

        call_command("seed_achievements")
        self._seed_badges()
        self._seed_extra_achievements()

        users = self._seed_users(
            limit=int(options["users"]),
            include_usernames=list(options.get("include_user") or []),
        )
        recent_albums = self._seed_recent_releases(limit=int(options["recent_releases"]), today=today)

        albums = list(
            Album.objects.select_related("artist")
            .annotate(songs_count=Count("songs", distinct=True))
            .filter(is_approved=True, artist__is_approved=True, songs_count__gt=1)
            .order_by("-release_date", "title")[:220]
        )
        if recent_albums:
            albums = list(dict.fromkeys(recent_albums + albums))
        songs = list(
            Song.objects.select_related("artist", "album")
            .filter(is_approved=True, artist__is_approved=True)
            .filter(Q(album__isnull=True) | Q(album__is_approved=True, album__artist__is_approved=True))
            .order_by("id")[:500]
        )
        artists = list(Artist.objects.filter(is_approved=True).order_by("name")[:80])

        if len(albums) < 10 or len(songs) < 10 or len(artists) < 5:
            raise RuntimeError("Not enough approved catalog data to seed realistic activity.")

        ratings_created = reviews_created = lists_created = list_items_created = 0
        friendships_created = likes_created = song_ratings_created = follows_created = 0

        for u_index, user in enumerate(users):
            user_albums = albums[u_index * 7:] + albums[: u_index * 7]
            user_songs = songs[u_index * 13:] + songs[: u_index * 13]
            user_artists = artists[u_index * 5:] + artists[: u_index * 5]

            for idx, album in enumerate(user_albums[: int(options["ratings_per_user"])]):
                when = now - timedelta(days=idx % 9, hours=(idx * 3) % 23)
                rating, created = AlbumRating.objects.update_or_create(
                    user=user,
                    album=album,
                    defaults={"rating": _rating_value(idx + u_index)},
                )
                _set_created_at(rating, when)
                if created:
                    ratings_created += 1

                activity, activity_created = UserActivity.objects.get_or_create(
                    actor=user,
                    activity_type=UserActivity.Type.RATE_ALBUM,
                    target_id=album.id,
                    defaults={"target_name": album.title, "rating": rating.rating},
                )
                UserActivity.objects.filter(pk=activity.pk).update(
                    target_name=album.title,
                    rating=rating.rating,
                    created_at=when,
                )

                if idx < 16:
                    like, created = AlbumLike.objects.get_or_create(user=user, album=album)
                    _set_created_at(like, when)
                    likes_created += int(created)

                if idx < 18:
                    listen, created = self._listen_for_day(user=user, album=album, day=today - timedelta(days=idx % 7))
                    if created:
                        UserActivity.objects.get_or_create(
                            actor=user,
                            activity_type=UserActivity.Type.LISTEN_ALBUM,
                            target_id=album.id,
                            defaults={"target_name": album.title},
                        )

            for idx, song in enumerate(user_songs[:18]):
                when = now - timedelta(hours=idx + 1) if idx < 5 else now - timedelta(days=idx % 6, hours=idx)
                sr, created = SongRating.objects.update_or_create(
                    user=user,
                    song=song,
                    defaults={"rating": _rating_value(idx + 2)},
                )
                _set_created_at(sr, when)
                song_ratings_created += int(created)
                if idx < 8:
                    sl, created = SongLike.objects.get_or_create(user=user, song=song)
                    _set_created_at(sl, when)

            for idx, album in enumerate(user_albums[: int(options["reviews_per_user"])]):
                review_title, review_content = REVIEW_TEXTS[(idx + u_index) % len(REVIEW_TEXTS)]
                review = AlbumReview.objects.filter(user=user, album=album).order_by("id").first()
                created = review is None
                if review is None:
                    review = AlbumReview.objects.create(
                        user=user,
                        album=album,
                        title=review_title,
                        content=review_content,
                    )
                else:
                    review.title = review_title
                    review.content = review_content
                    review.save(update_fields=["title", "content", "updated_at"])
                when = now - timedelta(days=idx % 6, hours=idx + u_index)
                AlbumReview.objects.filter(pk=review.pk).update(created_at=when, updated_at=when)
                reviews_created += int(created)

            for idx, artist in enumerate(user_artists[:12]):
                follow, created = ArtistFollow.objects.get_or_create(user=user, artist=artist)
                _set_created_at(follow, now - timedelta(days=idx % 6, minutes=idx * 11))
                follows_created += int(created)
                UserActivity.objects.get_or_create(
                    actor=user,
                    activity_type=UserActivity.Type.FOLLOW_ARTIST,
                    target_id=artist.id,
                    defaults={"target_name": artist.name},
                )

            for pos, album in enumerate(user_albums[:4], start=1):
                FavoriteAlbum.objects.update_or_create(user=user, position=pos, defaults={"album": album})
            for pos, song in enumerate(user_songs[:4], start=1):
                FavoriteSong.objects.update_or_create(user=user, position=pos, defaults={"song": song})

            created_lists, created_items = self._seed_lists(
                user=user,
                albums=user_albums,
                lists_per_user=int(options["lists_per_user"]),
                now=now,
            )
            lists_created += created_lists
            list_items_created += created_items

        friendships_created = self._seed_friendships(users=users, now=now)
        self._seed_review_engagement(users=users, now=now)
        self._seed_list_likes(users=users, now=now)
        self._award_demo_gamification(users)

        for user in users:
            update_all_achievement_progress(user)

        summary = {
            "users": len(users),
            "recent_releases": len(recent_albums),
            "ratings_created": ratings_created,
            "song_ratings_created": song_ratings_created,
            "reviews_created": reviews_created,
            "lists_created": lists_created,
            "list_items_created": list_items_created,
            "friendships_created": friendships_created,
            "album_likes_created": likes_created,
            "artist_follows_created": follows_created,
            "badges_total": Badge.objects.count(),
            "achievements_total": Achievement.objects.count(),
        }
        self.stdout.write(self.style.SUCCESS(f"Demo activity seeded: {summary}"))

    def _seed_users(self, *, limit: int, include_usernames: list[str]):
        users = []
        for username, email in DEMO_USERS[: max(1, min(limit, len(DEMO_USERS)))]:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "is_active": True},
            )
            if created:
                user.set_password("DemoPass123!")
                user.first_name = username.replace("demo_", "").title()
                user.save()
            privacy, _ = UserPrivacySettings.objects.get_or_create(user=user)
            privacy.email_verified = True
            privacy.public_lists = True
            privacy.public_activity = True
            privacy.public_compatibility = True
            privacy.save()
            users.append(user)
        for username in include_usernames:
            username = str(username or "").strip()
            if not username:
                continue
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"User not found, skipped: {username}"))
                continue
            privacy, _ = UserPrivacySettings.objects.get_or_create(user=user)
            privacy.email_verified = True
            privacy.public_lists = True
            privacy.public_activity = True
            privacy.public_compatibility = True
            privacy.save()
            if user not in users:
                users.append(user)
        return users

    def _seed_recent_releases(self, *, limit: int, today):
        artists = list(Artist.objects.filter(is_approved=True).order_by("name", "id")[: max(limit, 8)])
        release_titles = [
            "Drumuri Noi",
            "Cartierul Vorbeste",
            "Pasi de Noapte",
            "Ecouri de Violoncel",
            "Ritm de Vara",
            "Noapte Electrica",
            "Versuri Din Cartier",
            "Pe Alta Frecventa",
            "Lumini de Scena",
            "Zambet de Primavara",
            "Umbre Pe Asfalt",
            "Ritmuri Urbane",
            "Drum de Seara",
            "Club Session",
            "Semnale Din Oras",
            "Dincolo de Beat",
            "Vara In Doi",
            "Fara Pauza",
            "Nopti de Club",
            "Linii de Bas",
            "Ecouri Tarzii",
            "Pe Drumul Meu",
            "Cand Se Lasa Seara",
            "Unde S-a Dus Vara",
        ]
        track_titles = [
            ["Prima Statie", "Drumuri Noi", "Ultimul Refren"],
            ["Strada Se Aprinde", "Cartierul Vorbeste", "Dupa Blocuri"],
            ["Pasul Tacut", "Pasi de Noapte", "Dimineata Tarziu"],
            ["Tema de Deschidere", "Ecouri de Violoncel", "Final de Concert"],
            ["Ritm de Vara", "Pana La Rasarit", "Dans Pe Plaja"],
            ["Lumini In Club", "Noapte Electrica", "Dupa Miezul Noptii"],
            ["Rime Pe Beat", "Versuri Din Cartier", "Ultima Strofa"],
            ["Semnal Pierdut", "Pe Alta Frecventa", "In Alt Oras"],
        ]
        genre, _ = Genre.objects.get_or_create(name="lansari recente", defaults={"slug": "lansari-recente"})
        created_albums = []
        for idx, artist in enumerate(artists[:limit]):
            title = release_titles[idx % len(release_titles)]
            slug = f"{slugify(title)}-{slugify(artist.name)[:40]}"
            album, _ = Album.objects.update_or_create(
                slug=slug,
                defaults={
                    "artist": artist,
                    "title": title,
                    "description": "",
                    "cover_url": artist.image_url or "",
                    "release_date": today - timedelta(days=idx % 7),
                    "is_approved": True,
                    "mb_primary_type": "album",
                    "mb_secondary_types": "",
                },
            )
            album.genres.add(genre)
            current_tracks = track_titles[idx % len(track_titles)]
            for track in range(1, 4):
                Song.objects.update_or_create(
                    slug=f"{slug}-track-{track}",
                    defaults={
                        "album": album,
                        "artist": artist,
                        "title": current_tracks[track - 1],
                        "track_number": track,
                        "duration_seconds": 160 + track * 17,
                        "is_approved": True,
                    },
                )
            created_albums.append(album)
        return created_albums

    def _listen_for_day(self, *, user, album, day):
        listen, created = AlbumListen.objects.get_or_create(
            user=user,
            album=album,
            listened_date=day,
        )
        listened_at = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        AlbumListen.objects.filter(pk=listen.pk).update(listened_at=listened_at + timedelta(hours=12))
        return listen, created

    def _seed_lists(self, *, user, albums, lists_per_user: int, now):
        names = ["Rotatie curenta", "Albume romanesti bune", "De ascultat cu prietenii", "Top personal"]
        created_lists = 0
        created_items = 0
        for idx, name in enumerate(names[:lists_per_user]):
            lst, created = List.objects.get_or_create(
                user=user,
                name=name,
                defaults={
                    "description": "Lista cu albume alese pentru activitatea sociala.",
                    "is_public": True,
                },
            )
            _set_created_at(lst, now - timedelta(days=idx % 5, hours=idx))
            created_lists += int(created)
            for pos, album in enumerate(albums[idx * 5 : idx * 5 + 8], start=1):
                item, item_created = ListAlbum.objects.get_or_create(
                    list=lst,
                    album=album,
                    defaults={"position": pos},
                )
                ListAlbum.objects.filter(pk=item.pk).update(
                    position=pos,
                    added_at=now - timedelta(hours=pos) if pos <= 5 else now - timedelta(days=pos % 6, minutes=pos * 4),
                )
                created_items += int(item_created)
                UserActivity.objects.get_or_create(
                    actor=user,
                    activity_type=UserActivity.Type.LIST_ADD_ALBUM,
                    target_id=album.id,
                    defaults={"target_name": album.title},
                )
            UserActivity.objects.get_or_create(
                actor=user,
                activity_type=UserActivity.Type.CREATE_LIST,
                target_id=lst.id,
                defaults={"target_name": lst.name},
            )
        return created_lists, created_items

    def _seed_friendships(self, *, users, now):
        created = 0
        for idx, sender in enumerate(users):
            for receiver in users[idx + 1 : idx + 3]:
                fr, was_created = FriendRequest.objects.get_or_create(
                    sender=sender,
                    receiver=receiver,
                    defaults={"status": FriendRequest.Status.ACCEPTED},
                )
                if fr.status != FriendRequest.Status.ACCEPTED:
                    fr.status = FriendRequest.Status.ACCEPTED
                    fr.save(update_fields=["status"])
                _set_created_at(fr, now - timedelta(days=idx % 4, hours=idx))
                created += int(was_created)
        return created

    def _seed_review_engagement(self, *, users, now):
        reviews = list(AlbumReview.objects.select_related("user").filter(user__in=users)[:80])
        for idx, review in enumerate(reviews):
            for user in users:
                if user.id == review.user_id:
                    continue
                if (idx + user.id) % 2 == 0:
                    like, _ = AlbumReviewLike.objects.get_or_create(user=user, review=review)
                    _set_created_at(like, now - timedelta(days=idx % 5))
                if (idx + user.id) % 5 == 0:
                    comment_text = COMMENT_TEXTS[(idx + user.id) % len(COMMENT_TEXTS)]
                    comment, _ = ReviewComment.objects.get_or_create(
                        user=user,
                        review=review,
                        content=comment_text,
                    )
                    ReviewComment.objects.filter(pk=comment.pk).update(
                        created_at=now - timedelta(days=idx % 4),
                        updated_at=now - timedelta(days=idx % 4),
                    )

    def _seed_list_likes(self, *, users, now):
        lists = list(List.objects.filter(user__in=users, is_public=True))
        for idx, lst in enumerate(lists):
            for user in users:
                if user.id == lst.user_id:
                    continue
                if (idx + user.id) % 3 == 0:
                    like, _ = ListLike.objects.get_or_create(user=user, list=lst)
                    _set_created_at(like, now - timedelta(days=idx % 5))

    def _seed_badges(self):
        for code, name, description, category, rarity in BADGES:
            Badge.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                    "emoji": "*",
                    "category": category,
                    "rarity": rarity,
                },
            )

    def _seed_extra_achievements(self):
        for code, name, description, ach_type, target, points in ACHIEVEMENTS:
            Achievement.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": description,
                    "emoji": "*",
                    "type": ach_type,
                    "target": target,
                    "points": points,
                },
            )

    def _award_demo_gamification(self, users):
        badges = {b.code: b for b in Badge.objects.all()}
        achievements = {a.code: a for a in Achievement.objects.all()}
        for user in users:
            album_ratings = AlbumRating.objects.filter(user=user).count()
            song_ratings = SongRating.objects.filter(user=user).count()
            reviews = AlbumReview.objects.filter(user=user).count()
            lists = List.objects.filter(user=user).count()
            list_items = ListAlbum.objects.filter(list__user=user).count()
            friends = FriendRequest.objects.filter(
                Q(sender=user) | Q(receiver=user),
                status=FriendRequest.Status.ACCEPTED,
            ).count()
            follows = ArtistFollow.objects.filter(user=user).count()
            weekly_activity = UserActivity.objects.filter(
                actor=user,
                created_at__date__gte=timezone.localdate() - timedelta(days=7),
            ).count()

            badge_rules = [
                ("first_rating", album_ratings, 1),
                ("ten_ratings", album_ratings, 10),
                ("fifty_ratings", album_ratings, 50),
                ("first_review", reviews, 1),
                ("review_club", reviews, 5),
                ("list_maker", lists, 1),
                ("curator_plus", lists, 3),
                ("social_start", friends, 1),
                ("social_circle", friends, 3),
                ("artist_fan", follows, 5),
                ("song_rater", song_ratings, 10),
                ("weekly_active", weekly_activity, 1),
            ]
            for code, progress, target in badge_rules:
                badge = badges.get(code)
                if badge and progress >= target:
                    UserBadge.objects.update_or_create(
                        user=user,
                        badge=badge,
                        defaults={"progress": progress, "target": target},
                    )

            achievement_rules = [
                ("list_architect", list_items),
                ("social_listener", friends),
                ("song_scout", song_ratings),
                ("review_conversation", ReviewComment.objects.filter(review__user=user).count()),
                ("release_hunter", AlbumRating.objects.filter(user=user, album__slug__startswith="demo-fresh-release").count()),
            ]
            for code, progress in achievement_rules:
                achievement = achievements.get(code)
                if not achievement:
                    continue
                completed = progress >= achievement.target
                ua, _ = UserAchievement.objects.update_or_create(
                    user=user,
                    achievement=achievement,
                    defaults={
                        "progress": min(progress, achievement.target),
                        "is_completed": completed,
                        "unlocked_at": timezone.now() if completed else None,
                    },
                )
                if completed:
                    AchievementUnlock.objects.get_or_create(
                        user=user,
                        achievement=achievement,
                        achievement_code=achievement.code,
                        defaults={
                            "achievement_name": achievement.name,
                            "achievement_emoji": achievement.emoji,
                            "xp_awarded": achievement.points,
                        },
                    )

            xp, _ = UserXP.objects.get_or_create(user=user)
            completed_points = sum(
                ua.achievement.points
                for ua in UserAchievement.objects.select_related("achievement").filter(user=user, is_completed=True)
            )
            xp.total_xp = max(xp.total_xp, completed_points)
            xp.level = max(1, completed_points // 500 + 1)
            xp.current_level_xp = completed_points % 500
            xp.save()
