from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Badge, UserBadge, Achievement, UserAchievement, UserXP
from .gamification_serializers import (
    BadgeSerializer, 
    UserBadgeSerializer, 
    AchievementSerializer, 
    UserAchievementSerializer,
    UserXPSerializer,
    UserGamificationStatsSerializer,
)
from .gamification import weekly_challenges_payload_for, streak_payload_for


class BadgeViewSet(viewsets.ReadOnlyModelViewSet):
                                                 
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def by_category(self, request):
                                            
        category = request.query_params.get('category')
        if category:
            badges = Badge.objects.filter(category=category)
        else:
            badges = Badge.objects.all()
        serializer = BadgeSerializer(badges, many=True)
        return Response(serializer.data)


class UserBadgeViewSet(viewsets.ReadOnlyModelViewSet):
                              
    permission_classes = [IsAuthenticated]
    serializer_class = UserBadgeSerializer

    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user).select_related('badge')

    @action(detail=False, methods=['get'])
    def my_badges(self, request):
                                                       
        badges = self.get_queryset()
        serializer = UserBadgeSerializer(badges, many=True)
        return Response(serializer.data)


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
                                                       
    queryset = Achievement.objects.all()
    serializer_class = AchievementSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def by_type(self, request):
                                              
        achievement_type = request.query_params.get('type')
        if achievement_type:
            achievements = Achievement.objects.filter(type=achievement_type)
        else:
            achievements = Achievement.objects.all()
        serializer = AchievementSerializer(achievements, many=True)
        return Response(serializer.data)


class UserAchievementViewSet(viewsets.ReadOnlyModelViewSet):
                                          
    permission_classes = [IsAuthenticated]
    serializer_class = UserAchievementSerializer

    def get_queryset(self):
        return UserAchievement.objects.filter(user=self.request.user).select_related('achievement')

    @action(detail=False, methods=['get'])
    def my_achievements(self, request):
                                                       
        achievements = self.get_queryset()
        serializer = UserAchievementSerializer(achievements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unlocked(self, request):
                                            
        achievements = self.get_queryset().filter(is_completed=True)
        serializer = UserAchievementSerializer(achievements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def in_progress(self, request):
                                                
        achievements = self.get_queryset().filter(is_completed=False)
        serializer = UserAchievementSerializer(achievements, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def refresh(self, request):
                                                                  
        from interactions.achievement_tracker import update_all_achievement_progress
        
        user = request.user
        unlocked_codes = update_all_achievement_progress(user)
        
                                  
        achievements = self.get_queryset()
        serializer = UserAchievementSerializer(achievements, many=True)
        
        return Response({
            'message': f'Achievements updated. Unlocked: {unlocked_codes}',
            'unlocked_achievements': unlocked_codes,
            'achievements': serializer.data,
        }, status=status.HTTP_200_OK)


class UserXPViewSet(viewsets.ReadOnlyModelViewSet):
                                         
    permission_classes = [IsAuthenticated]
    serializer_class = UserXPSerializer

    def get_queryset(self):
        return UserXP.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_xp(self, request):
                                             
        try:
            user_xp = UserXP.objects.get(user=request.user)
        except UserXP.DoesNotExist:
                                     
            user_xp = UserXP.objects.create(user=request.user)
        
        serializer = UserXPSerializer(user_xp)
        return Response(serializer.data)


class GamificationStatsView(viewsets.ViewSet):
                                              
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_stats(self, request):
                                                         
        user = request.user

                               
        user_xp, _ = UserXP.objects.get_or_create(user=user)

                    
        badges = UserBadge.objects.filter(user=user).select_related('badge')
        badges_serialized = UserBadgeSerializer(badges, many=True).data

                          
        achievements = UserAchievement.objects.filter(user=user).select_related('achievement')
        achievements_serialized = UserAchievementSerializer(achievements, many=True).data

                               
        weekly_challenges = weekly_challenges_payload_for(user)

                     
        streaks = streak_payload_for(user)

        return Response({
            'user_xp': UserXPSerializer(user_xp).data,
            'badges': badges_serialized,
            'achievements': achievements_serialized,
            'badges_count': len(badges_serialized),
            'achievements_count': len(achievements_serialized),
            'achievements_unlocked_count': sum(1 for a in achievements_serialized if a['is_completed']),
            'weekly_challenges': weekly_challenges,
            'streaks': streaks,
        })
