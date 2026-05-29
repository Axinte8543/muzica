from rest_framework import serializers
from .models import Badge, UserBadge, Achievement, UserAchievement, UserXP


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ['id', 'code', 'name', 'description', 'emoji', 'category', 'rarity', 'created_at']
        read_only_fields = ['created_at']


class UserBadgeSerializer(serializers.ModelSerializer):
    badge = BadgeSerializer(read_only=True)

    class Meta:
        model = UserBadge
        fields = ['id', 'badge', 'earned_at', 'progress', 'target']
        read_only_fields = ['earned_at']


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ['id', 'code', 'name', 'description', 'emoji', 'type', 'target', 'points', 'created_at']
        read_only_fields = ['created_at']


class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)

    class Meta:
        model = UserAchievement
        fields = ['id', 'achievement', 'progress', 'unlocked_at', 'is_completed', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class UserXPSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserXP
        fields = ['id', 'total_xp', 'level', 'current_level_xp', 'last_updated']
        read_only_fields = ['last_updated']


class UserGamificationStatsSerializer(serializers.Serializer):
    """Combined gamification stats for user"""
    user_xp = UserXPSerializer(read_only=True)
    badges = UserBadgeSerializer(many=True, read_only=True)
    achievements = UserAchievementSerializer(many=True, read_only=True)
    badges_count = serializers.SerializerMethodField()
    achievements_count = serializers.SerializerMethodField()
    achievements_unlocked_count = serializers.SerializerMethodField()

    def get_badges_count(self, obj):
        if 'badges' in obj:
            return len(obj['badges'])
        return 0

    def get_achievements_count(self, obj):
        if 'achievements' in obj:
            return len(obj['achievements'])
        return 0

    def get_achievements_unlocked_count(self, obj):
        if 'achievements' in obj:
            return sum(1 for a in obj['achievements'] if a['is_completed'])
        return 0
