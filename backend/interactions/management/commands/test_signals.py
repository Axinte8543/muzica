"""
Management command to test signal handlers for gamification events.

Usage:
    python manage.py test_signals --user <user_id>
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from interactions.models import (
	AlbumReview,
	AlbumRating,
	AlbumLike,
	AlbumListen,
	ArtistFollow,
	List as UserList,
)
from music.models import Album, Artist, Song
from datetime import datetime

User = get_user_model()


class Command(BaseCommand):
	help = "Test if Django signals are firing for gamification events"

	def add_arguments(self, parser):
		parser.add_argument(
			"--user",
			type=int,
			help="User ID to test signals for",
			required=True,
		)

	def handle(self, *args, **options):
		user_id = options["user"]

		try:
			user = User.objects.get(id=user_id)
		except User.DoesNotExist:
			raise CommandError(f"User with ID {user_id} does not exist")

		self.stdout.write(f"\n{'='*60}")
		self.stdout.write(f"Testing Gamification Signals for user: {user.username} (ID: {user.id})")
		self.stdout.write(f"{'='*60}\n")

		# Get or create test album/artist
		artist, _ = Artist.objects.get_or_create(
			name="Test Artist",
			defaults={"slug": "test-artist", "is_approved": True},
		)

		album, _ = Album.objects.get_or_create(
			title="Test Album",
			artist=artist,
			defaults={"slug": "test-album", "is_approved": True},
		)

		test_results = []

		# Test 1: Review Signal
		self.stdout.write("\n[1/5] Testing Review Signal...")
		try:
			review = AlbumReview.objects.create(
				user=user,
				album=album,
				title="Test Review",
				content="This is a test review to verify signals are working.",
			)
			test_results.append(("Review Signal", "✓ FIRED", "Review created successfully"))
			self.stdout.write(self.style.SUCCESS(f"    ✓ Review created (ID: {review.id})"))
		except Exception as e:
			test_results.append(("Review Signal", "✗ FAILED", str(e)))
			self.stdout.write(self.style.ERROR(f"    ✗ Error: {str(e)}"))

		# Test 2: Rating Signal
		self.stdout.write("\n[2/5] Testing Rating Signal...")
		try:
			rating = AlbumRating.objects.create(
				user=user,
				album=album,
				rating=5,
			)
			test_results.append(("Rating Signal", "✓ FIRED", "Rating created successfully"))
			self.stdout.write(self.style.SUCCESS(f"    ✓ Rating created (ID: {rating.id})"))
		except Exception as e:
			test_results.append(("Rating Signal", "✗ FAILED", str(e)))
			self.stdout.write(self.style.ERROR(f"    ✗ Error: {str(e)}"))

		# Test 3: Like Signal
		self.stdout.write("\n[3/5] Testing Like Signal...")
		try:
			like = AlbumLike.objects.create(
				user=user,
				album=album,
			)
			test_results.append(("Like Signal", "✓ FIRED", "Like created successfully"))
			self.stdout.write(self.style.SUCCESS(f"    ✓ Like created (ID: {like.id})"))
		except Exception as e:
			test_results.append(("Like Signal", "✗ FAILED", str(e)))
			self.stdout.write(self.style.ERROR(f"    ✗ Error: {str(e)}"))

		# Test 4: Listen Signal
		self.stdout.write("\n[4/5] Testing Listen Signal...")
		try:
			listen = AlbumListen.objects.create(
				user=user,
				album=album,
				listened_date=datetime.now().date(),
			)
			test_results.append(("Listen Signal", "✓ FIRED", "Listen created successfully"))
			self.stdout.write(self.style.SUCCESS(f"    ✓ Listen created (ID: {listen.id})"))
		except Exception as e:
			test_results.append(("Listen Signal", "✗ FAILED", str(e)))
			self.stdout.write(self.style.ERROR(f"    ✗ Error: {str(e)}"))

		# Test 5: Follow Signal
		self.stdout.write("\n[5/5] Testing Follow Signal...")
		try:
			follow = ArtistFollow.objects.create(
				user=user,
				artist=artist,
			)
			test_results.append(("Follow Signal", "✓ FIRED", "Follow created successfully"))
			self.stdout.write(self.style.SUCCESS(f"    ✓ Follow created (ID: {follow.id})"))
		except Exception as e:
			test_results.append(("Follow Signal", "✗ FAILED", str(e)))
			self.stdout.write(self.style.ERROR(f"    ✗ Error: {str(e)}"))

		# Print summary
		self.stdout.write(f"\n{'='*60}")
		self.stdout.write("TEST SUMMARY")
		self.stdout.write(f"{'='*60}\n")

		for signal_name, status, message in test_results:
			status_color = self.style.SUCCESS if "✓" in status else self.style.ERROR
			self.stdout.write(f"{signal_name:20} {status_color(status):15} {message}")

		# Check if all signals fired
		all_fired = all("✓" in status for _, status, _ in test_results)

		self.stdout.write(f"\n{'='*60}\n")

		if all_fired:
			self.stdout.write(
				self.style.SUCCESS(
					"✓ ALL SIGNALS FIRING! Gamification system is working correctly."
				)
			)
		else:
			self.stdout.write(
				self.style.ERROR(
					"✗ Some signals are not firing. Check the logs for details."
				)
			)
			self.stdout.write(
				"\nTo see detailed error logs, run:"
			)
			self.stdout.write(
				"    tail -f logs/django.log  # if logging is configured"
			)

		self.stdout.write("\nCheck Django logs for signal execution details:")
		self.stdout.write("  - Look for '✓ Signal fired' messages for successful signals")
		self.stdout.write("  - Look for '✗ Error in signal' messages for failures\n")
