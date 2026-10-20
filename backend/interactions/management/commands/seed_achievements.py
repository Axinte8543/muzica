\
\
\
\
\
   

from django.core.management.base import BaseCommand
from interactions.models import Achievement


ACHIEVEMENTS_DATA = [
                            
    {
        'code': 'reviewer_5',
        'name': 'Critic',
        'description': 'Write 5 album reviews',
        'emoji': '📝',
        'type': 'milestone',
        'target': 5,
        'points': 25,
    },
    {
        'code': 'rater_10',
        'name': 'Rating Master',
        'description': 'Rate 10 albums',
        'emoji': '⭐',
        'type': 'milestone',
        'target': 10,
        'points': 20,
    },
    {
        'code': 'listener_50',
        'name': 'Avid Listener',
        'description': 'Listen to 50 distinct albums',
        'emoji': '🎵',
        'type': 'milestone',
        'target': 50,
        'points': 50,
    },
    {
        'code': 'fan_20',
        'name': 'Super Fan',
        'description': 'Follow 20 artists',
        'emoji': '👤',
        'type': 'milestone',
        'target': 20,
        'points': 30,
    },
    {
        'code': 'liker_25',
        'name': 'Enthusiast',
        'description': 'Like 25 albums',
        'emoji': '❤️',
        'type': 'milestone',
        'target': 25,
        'points': 25,
    },
    {
        'code': 'list_creator',
        'name': 'Curator',
        'description': 'Create your first list',
        'emoji': '📋',
        'type': 'milestone',
        'target': 1,
        'points': 15,
    },
    
                         
    {
        'code': 'review_streak_5',
        'name': 'Consistent Critic',
        'description': 'Post reviews for 5 consecutive days',
        'emoji': '🔥',
        'type': 'streak',
        'target': 5,
        'points': 35,
    },
    {
        'code': 'listen_streak_7',
        'name': 'Daily Listener',
        'description': 'Listen to albums for 7 consecutive days',
        'emoji': '🎶',
        'type': 'streak',
        'target': 7,
        'points': 40,
    },
    {
        'code': 'rating_streak_3',
        'name': 'Rating Streak',
        'description': 'Rate albums for 3 consecutive days',
        'emoji': '⚡',
        'type': 'streak',
        'target': 3,
        'points': 20,
    },
    
                            
    {
        'code': 'romanian_explorer',
        'name': 'Romanian Explorer',
        'description': 'Listen to 10 different artists',
        'emoji': '🇷🇴',
        'type': 'discovery',
        'target': 10,
        'points': 30,
    },
    {
        'code': 'genre_explorer',
        'name': 'Genre Master',
        'description': 'Listen to albums from 15 different genres',
        'emoji': '🎸',
        'type': 'discovery',
        'target': 15,
        'points': 40,
    },
    {
        'code': 'era_explorer',
        'name': 'Time Traveler',
        'description': 'Listen to albums from 5 different decades',
        'emoji': '⏱️',
        'type': 'discovery',
        'target': 5,
        'points': 35,
    },
]


class Command(BaseCommand):
    help = 'Seed achievements into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing achievements',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        created_count = 0
        updated_count = 0

        for achievement_data in ACHIEVEMENTS_DATA:
            code = achievement_data['code']
            
            if force:
                                                     
                Achievement.objects.filter(code=code).delete()
                achievement, created = Achievement.objects.create(**achievement_data), True
                created_count += 1
            else:
                               
                achievement, created = Achievement.objects.get_or_create(
                    code=code,
                    defaults=achievement_data
                )
                if created:
                    created_count += 1
                else:
                                      
                    for field, value in achievement_data.items():
                        if field != 'code':
                            setattr(achievement, field, value)
                    achievement.save()
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Seeding complete: {created_count} created, {updated_count} updated'
            )
        )
