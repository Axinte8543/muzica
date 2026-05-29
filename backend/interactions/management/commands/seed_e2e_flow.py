from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from interactions.models import AlbumRating, ChatMessage, FriendRequest
from music.models import Album, Artist, Genre, Song


ALICE_USERNAME = "e2e_alice"
BOB_USERNAME = "e2e_bob"
PASSWORD = "E2E_Test_123!"
ARTIST_NAME = "E2E Flow Artist"
ARTIST_SLUG = "e2e-flow-artist"


@dataclass(frozen=True)
class AlbumSeed:
    title: str
    slug: str
    release_date: date
    track_title: str


ALBUMS: tuple[AlbumSeed, ...] = (
    AlbumSeed("E2E Album Sunrise", "e2e-album-sunrise", date(2023, 1, 10), "Sunrise"),
    AlbumSeed("E2E Album Skyline", "e2e-album-skyline", date(2023, 3, 14), "Skyline"),
    AlbumSeed("E2E Album Aurora", "e2e-album-aurora", date(2023, 5, 20), "Aurora"),
    AlbumSeed("E2E Album Midnight", "e2e-album-midnight", date(2023, 7, 2), "Midnight"),
)


def _set_password(user, raw_password: str):
    user.set_password(raw_password)
    user.save(update_fields=["password"])


class Command(BaseCommand):
    help = "Seed a deterministic dataset for the auth -> messaging -> recommendations Playwright flow."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previously seeded E2E data before recreating it.",
        )

    def handle(self, *args, **options):
        reset = bool(options.get("reset"))
        User = get_user_model()

        with transaction.atomic():
            if reset:
                User.objects.filter(username__in=[ALICE_USERNAME, BOB_USERNAME]).delete()
                Song.objects.filter(slug__startswith="e2e-").delete()
                Album.objects.filter(slug__startswith="e2e-").delete()
                Artist.objects.filter(slug=ARTIST_SLUG).delete()

            genre, _ = Genre.objects.get_or_create(
                name="E2E Genre",
                defaults={"slug": slugify("E2E Genre") or "e2e-genre"},
            )

            artist, _ = Artist.objects.update_or_create(
                slug=ARTIST_SLUG,
                defaults={
                    "name": ARTIST_NAME,
                    "is_romanian": True,
                    "is_approved": True,
                },
            )
            artist.genres.set([genre])

            album_objs: list[Album] = []
            for seed in ALBUMS:
                album, _ = Album.objects.update_or_create(
                    slug=seed.slug,
                    defaults={
                        "artist": artist,
                        "title": seed.title,
                        "release_date": seed.release_date,
                        "cover_url": "",
                        "is_approved": True,
                    },
                )
                album.genres.set([genre])
                album_objs.append(album)

                Song.objects.update_or_create(
                    slug=f"{seed.slug}-song",
                    defaults={
                        "album": album,
                        "artist": artist,
                        "title": seed.track_title,
                        "track_number": 1,
                        "duration_seconds": 180,
                        "is_approved": True,
                    },
                )

            alice, _ = User.objects.update_or_create(
                username=ALICE_USERNAME,
                defaults={"email": "e2e_alice@example.com"},
            )
            bob, _ = User.objects.update_or_create(
                username=BOB_USERNAME,
                defaults={"email": "e2e_bob@example.com"},
            )
            _set_password(alice, PASSWORD)
            _set_password(bob, PASSWORD)

            # Clear and rebuild the interaction layer to keep the dataset deterministic.
            ChatMessage.objects.filter(sender__in=[alice, bob], recipient__in=[alice, bob]).delete()
            AlbumRating.objects.filter(user__in=[alice, bob]).delete()
            FriendRequest.objects.filter(sender__in=[alice, bob], receiver__in=[alice, bob]).delete()

            FriendRequest.objects.create(sender=alice, receiver=bob, status=FriendRequest.Status.ACCEPTED)
            reverse_request, _ = FriendRequest.objects.get_or_create(
                sender=bob,
                receiver=alice,
                defaults={"status": FriendRequest.Status.ACCEPTED},
            )
            if reverse_request.status != FriendRequest.Status.ACCEPTED:
                reverse_request.status = FriendRequest.Status.ACCEPTED
                reverse_request.save(update_fields=["status"])

            # Ratings deliberately overlap to force non-empty recommendations.
            AlbumRating.objects.update_or_create(user=alice, album=album_objs[0], defaults={"rating": 5})
            AlbumRating.objects.update_or_create(user=alice, album=album_objs[1], defaults={"rating": 4})
            AlbumRating.objects.update_or_create(user=bob, album=album_objs[0], defaults={"rating": 4})
            AlbumRating.objects.update_or_create(user=bob, album=album_objs[1], defaults={"rating": 5})
            AlbumRating.objects.update_or_create(user=bob, album=album_objs[2], defaults={"rating": 5})
            AlbumRating.objects.update_or_create(user=bob, album=album_objs[3], defaults={"rating": 4})

            # Seed a starter message so the conversation list is non-empty.
            ChatMessage.objects.create(
                sender=bob,
                recipient=alice,
                content="Salut! Testăm conversația end-to-end.",
            )

        self.stdout.write(self.style.SUCCESS(
            "Seeded E2E flow data: users=e2e_alice/e2e_bob, artist='E2E Flow Artist', albums=4"
        ))
        self.stdout.write(self.style.SUCCESS(f"Credentials: username={ALICE_USERNAME} password={PASSWORD}"))
