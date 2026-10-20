\
\
\
\
\
\
   

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from interactions.achievement_tracker import update_all_achievement_progress
from interactions.models import UserAchievement

User = get_user_model()


class Command(BaseCommand):
    help = 'Test and display achievement progress for a user'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Username to check achievements for'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update all achievements for the user',
        )

    def handle(self, *args, **options):
        username = options['username']
        update = options.get('update', False)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User "{username}" not found')
            )
            return

        self.stdout.write(self.style.SUCCESS(f'\n🎮 Achievement Progress for @{user.username}\n'))

        if update:
            self.stdout.write('⏳ Updating achievements...')
            unlocked = update_all_achievement_progress(user)
            if unlocked:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Unlocked: {", ".join(unlocked)}')
                )
            else:
                self.stdout.write('ℹ️ No new achievements unlocked')
            self.stdout.write('')

                                  
        user_achievements = UserAchievement.objects.filter(user=user).select_related(
            'achievement'
        ).order_by('-is_completed', 'achievement__type')

        if not user_achievements.exists():
            self.stdout.write('  No achievements started yet\n')
            return

                       
        by_type = {}
        for ua in user_achievements:
            achv_type = ua.achievement.get_type_display()
            if achv_type not in by_type:
                by_type[achv_type] = []
            by_type[achv_type].append(ua)

        for achv_type in ['Milestone Achievement', 'Streak Achievement', 'Discovery Achievement']:
            if achv_type not in by_type:
                continue
            
            self.stdout.write(self.style.SUCCESS(f'\n{achv_type}:'))
            
            for ua in by_type[achv_type]:
                status = '✅' if ua.is_completed else '🔄'
                percent = int((ua.progress / ua.achievement.target) * 100) if ua.achievement.target > 0 else 0
                bar_filled = int(percent / 10)
                bar_empty = 10 - bar_filled
                progress_bar = '█' * bar_filled + '░' * bar_empty
                
                self.stdout.write(
                    f'  {status} {ua.achievement.emoji} {ua.achievement.name}\n'
                    f'     {progress_bar} {ua.progress}/{ua.achievement.target} ({percent}%)\n'
                    f'     {ua.achievement.description}\n'
                )

                 
        total = user_achievements.count()
        completed = user_achievements.filter(is_completed=True).count()
        self.stdout.write(
            self.style.SUCCESS(
                f'\n📊 Summary: {completed}/{total} achievements unlocked'
            )
        )
        self.stdout.write('')
