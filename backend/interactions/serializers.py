from rest_framework import serializers

from .models import (
        CatalogChangelogEvent,
    AlbumLike,
    AlbumListen,
    AlbumRating,
    AlbumReview,
    AlbumReviewDraft,
    AlbumReviewEdit,
    AlbumReviewLike,
    AlbumReviewReaction,
    AchievementUnlock,
    ArtistFollow,
    ArtistRating,
    ChatMessage,
    ChatTypingStatus,
    CorrectionReport,
        ReviewCommentEdit,
    FavoriteAlbum,
    FriendRequest,
    List,
    ListAlbum,
    ListAlbumNote,
    ListLike,
    ListMembership,
    ListTag,
    MetadataSuggestion,
    ModerationReport,
    NotificationPreferences,
    ReviewComment,
    ReviewCommentMention,
    ReviewCommentReaction,
    SongComment,
    SongCommentMention,
    SongCommentEdit,
    SongCommentReaction,
    SongRating,
    UserActivity,
    UserOnboarding,
    WantToListen,
)


class ListMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()


class ListCollaboratorUpsertSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=ListMembership.Role.choices, required=False)

    def validate_username(self, value: str):
        username = str(value or '').strip()
        if not username:
            raise serializers.ValidationError('username is required')
        return username


class ListCollaboratorRemoveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)


class ListTagsUpdateSerializer(serializers.Serializer):
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        allow_empty=True,
        required=True,
    )

    def validate_tags(self, value):
        names = []
        for raw in value or []:
            name = str(raw or '').strip()
            if not name:
                continue
                                                
            name = ' '.join(name.split())
            names.append(name)
                               
        seen = set()
        out = []
        for n in names:
            key = n.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(n)
        return out


class ListAlbumNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListAlbumNote
        fields = ['note', 'updated_at']
        read_only_fields = ['updated_at']


class ListAlbumNoteUpdateSerializer(serializers.Serializer):
    note = serializers.CharField(required=True, allow_blank=True)

    def validate_note(self, value: str):
                                                   
        return str(value or '')


class ModerationReportCreateSerializer(serializers.Serializer):
                                                     
    target_type = serializers.ChoiceField(choices=['review', 'review_comment', 'song_comment'])
    target_id = serializers.IntegerField(min_value=1)
    reason_code = serializers.ChoiceField(choices=ModerationReport.ReasonCode.choices, required=False)
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate_reason(self, value: str):
        return str(value or '')


class MetadataSuggestionCreateSerializer(serializers.Serializer):
                                    
    target_type = serializers.ChoiceField(choices=['artist', 'album', 'song'])
    target_id = serializers.IntegerField(min_value=1)
    kind = serializers.ChoiceField(choices=MetadataSuggestion.Kind.choices)
    payload = serializers.JSONField(required=False)
    note = serializers.CharField(required=False, allow_blank=True)

    def validate_note(self, value: str):
        return str(value or '')

    def validate(self, attrs):
        kind = attrs.get('kind')
        payload = attrs.get('payload')
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise serializers.ValidationError({'payload': 'payload must be a JSON object'})

        if kind == MetadataSuggestion.Kind.RELEASE_DATE:
            raw = payload.get('release_date', None)
            if raw in (None, ''):
                raise serializers.ValidationError({'payload': {'release_date': 'release_date is required'}})
            try:
                parsed = serializers.DateField().to_internal_value(raw)
            except serializers.ValidationError as e:
                raise serializers.ValidationError({'payload': {'release_date': e.detail}})
            payload['release_date'] = parsed.isoformat()

        elif kind == MetadataSuggestion.Kind.COVER_URL:
            raw = str(payload.get('cover_url', '') or '').strip()
            if not raw:
                raise serializers.ValidationError({'payload': {'cover_url': 'cover_url is required'}})
            if len(raw) > 500:
                raise serializers.ValidationError({'payload': {'cover_url': 'cover_url is too long'}})
            payload['cover_url'] = raw

        elif kind == MetadataSuggestion.Kind.IMAGE_URL:
            raw = str(payload.get('image_url', '') or '').strip()
            if not raw:
                raise serializers.ValidationError({'payload': {'image_url': 'image_url is required'}})
            if len(raw) > 500:
                raise serializers.ValidationError({'payload': {'image_url': 'image_url is too long'}})
            payload['image_url'] = raw

        elif kind == MetadataSuggestion.Kind.TRACKLIST:
            tracks = payload.get('tracks')
            if not isinstance(tracks, list) or not tracks:
                raise serializers.ValidationError({'payload': {'tracks': 'tracks must be a non-empty list'}})
            if len(tracks) > 200:
                raise serializers.ValidationError({'payload': {'tracks': 'too many tracks'}})
            norm_tracks = []
            seen_numbers = set()
            for i, t in enumerate(tracks):
                if not isinstance(t, dict):
                    raise serializers.ValidationError({'payload': {'tracks': f'item {i} must be an object'}})
                title = str(t.get('title', '') or '').strip()
                if not title:
                    raise serializers.ValidationError({'payload': {'tracks': f'item {i} title is required'}})
                track_number = t.get('track_number', None)
                try:
                    track_number_int = int(track_number)
                except (TypeError, ValueError):
                    raise serializers.ValidationError({'payload': {'tracks': f'item {i} track_number must be an integer'}})
                if track_number_int <= 0:
                    raise serializers.ValidationError({'payload': {'tracks': f'item {i} track_number must be > 0'}})
                if track_number_int in seen_numbers:
                    raise serializers.ValidationError({'payload': {'tracks': f'duplicate track_number: {track_number_int}'}})
                seen_numbers.add(track_number_int)
                duration = t.get('duration_seconds', None)
                duration_int = None
                if duration not in (None, ''):
                    try:
                        duration_int = int(duration)
                    except (TypeError, ValueError):
                        raise serializers.ValidationError({'payload': {'tracks': f'item {i} duration_seconds must be an integer'}})
                    duration_int = max(0, duration_int)
                norm_tracks.append({
                    'title': title,
                    'track_number': track_number_int,
                    'duration_seconds': duration_int,
                })
            norm_tracks.sort(key=lambda x: x['track_number'])
            payload['tracks'] = norm_tracks

        elif kind in {MetadataSuggestion.Kind.BIO, MetadataSuggestion.Kind.ALIASES, MetadataSuggestion.Kind.DESCRIPTION}:
            key = {
                MetadataSuggestion.Kind.BIO: 'bio',
                MetadataSuggestion.Kind.ALIASES: 'aliases',
                MetadataSuggestion.Kind.DESCRIPTION: 'description',
            }[kind]
            raw = str(payload.get(key, '') or '').strip()
            if not raw:
                raise serializers.ValidationError({'payload': {key: f'{key} is required'}})
            payload[key] = raw

                                    

        attrs['payload'] = payload
        return attrs


class ModerationReportSerializer(serializers.ModelSerializer):
    reporter_id = serializers.IntegerField(source='reporter.id', read_only=True)
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()
    resolved_by_username = serializers.CharField(source='resolved_by.username', read_only=True)

    class Meta:
        model = ModerationReport
        fields = [
            'id',
            'target_type',
            'target_id',
            'reason_code',
            'reason',
            'status',
            'created_at',
            'resolved_at',
            'resolution_reason',
            'resolution_feedback',
            'reporter_id',
            'reporter_username',
            'resolved_by_username',
        ]

    def get_target_type(self, obj: ModerationReport):
        if obj.review_id:
            return 'review'
        if obj.review_comment_id:
            return 'review_comment'
        return 'song_comment'

    def get_target_id(self, obj: ModerationReport):
        return int(obj.review_id or obj.review_comment_id or obj.song_comment_id)


class MetadataSuggestionSerializer(serializers.ModelSerializer):
    suggester_id = serializers.IntegerField(source='suggester.id', read_only=True)
    suggester_username = serializers.CharField(source='suggester.username', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True)
    target_type = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()
    target_name = serializers.SerializerMethodField()
    target_slug = serializers.SerializerMethodField()

    class Meta:
        model = MetadataSuggestion
        fields = [
            'id',
            'target_type',
            'target_id',
            'target_name',
            'target_slug',
            'kind',
            'payload',
            'note',
            'status',
            'created_at',
            'reviewed_at',
            'reviewed_by_username',
            'decision_note',
            'applied',
            'suggester_id',
            'suggester_username',
        ]
        read_only_fields = fields

    def get_target_type(self, obj: MetadataSuggestion):
        if obj.artist_id:
            return 'artist'
        if obj.album_id:
            return 'album'
        return 'song'

    def get_target_id(self, obj: MetadataSuggestion):
        return int(obj.artist_id or obj.album_id or obj.song_id)

    def get_target_name(self, obj: MetadataSuggestion):
        target = obj.artist or obj.album or obj.song
        if not target:
            return ''
        return str(getattr(target, 'name', None) or getattr(target, 'title', '') or '')

    def get_target_slug(self, obj: MetadataSuggestion):
        target = obj.artist or obj.album or obj.song
        if not target:
            return ''
        return str(getattr(target, 'slug', '') or '')


class AlbumReviewEditSerializer(serializers.ModelSerializer):
    edited_by_username = serializers.CharField(source='edited_by.username', read_only=True)

    class Meta:
        model = AlbumReviewEdit
        fields = [
            'id',
            'edited_at',
            'edited_by_username',
            'previous_title',
            'previous_content',
        ]
        read_only_fields = fields


class AlbumReviewDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlbumReviewDraft
        fields = ['title', 'content', 'updated_at']
        read_only_fields = ['updated_at']


class AlbumReviewDraftUpsertSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)

    def validate_title(self, value: str):
        return str(value or '')

    def validate_content(self, value: str):
        return str(value or '')


class FollowStatusSerializer(serializers.Serializer):
    is_following = serializers.BooleanField()


class RatingInputSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)


class AlbumReviewCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    content = serializers.CharField()


class AlbumReviewUpdateSerializer(serializers.Serializer):
                                                         
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    content = serializers.CharField()


class ReviewCommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField()
    parent_id = serializers.IntegerField(min_value=1, required=False)

    def validate_content(self, value: str):
        content = str(value).strip()
        if not content:
            raise serializers.ValidationError("Content is required")
        return content


class ReviewCommentUpdateSerializer(serializers.Serializer):
    content = serializers.CharField()

    def validate_content(self, value: str):
        content = str(value).strip()
        if not content:
            raise serializers.ValidationError("Content is required")
        return content


class ReviewCommentSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)
    review_id = serializers.IntegerField(source="review.id", read_only=True)
    parent_id = serializers.IntegerField(source="parent.id", read_only=True, allow_null=True)

    class Meta:
        model = ReviewComment
        fields = [
            "id",
            "review_id",
            "parent_id",
            "content",
            "created_at",
            "updated_at",
            "user_id",
            "user_username",
        ]


class ReviewCommentEditSerializer(serializers.ModelSerializer):
    edited_by_username = serializers.CharField(source='edited_by.username', read_only=True)

    class Meta:
        model = ReviewCommentEdit
        fields = [
            'id',
            'edited_at',
            'edited_by_username',
            'previous_content',
        ]
        read_only_fields = fields


class SongCommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField()
    parent_id = serializers.IntegerField(min_value=1, required=False)

    def validate_content(self, value: str):
        content = str(value).strip()
        if not content:
            raise serializers.ValidationError("Content is required")
        return content


class SongCommentSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)
    song_id = serializers.IntegerField(source="song.id", read_only=True)
    parent_id = serializers.IntegerField(source="parent.id", read_only=True, allow_null=True)

    class Meta:
        model = SongComment
        fields = [
            "id",
            "song_id",
            "parent_id",
            "content",
            "created_at",
            "updated_at",
            "user_id",
            "user_username",
        ]


class SongCommentEditSerializer(serializers.ModelSerializer):
    edited_by_username = serializers.CharField(source='edited_by.username', read_only=True)

    class Meta:
        model = SongCommentEdit
        fields = [
            'id',
            'edited_at',
            'edited_by_username',
            'previous_content',
        ]
        read_only_fields = fields


class ReviewCommentReactionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ReviewCommentReaction
        fields = [
            'id',
            'emoji',
            'user_id',
            'user_username',
            'created_at',
        ]
        read_only_fields = fields


class AlbumReviewReactionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AlbumReviewReaction
        fields = [
            'id',
            'emoji',
            'user_id',
            'user_username',
            'created_at',
        ]
        read_only_fields = fields


class AlbumReviewReactionCreateSerializer(serializers.Serializer):
    emoji = serializers.CharField(max_length=10)

    def validate_emoji(self, value):
        valid_emojis = [choice[0] for choice in AlbumReviewReaction.EMOJI_CHOICES]
        if value not in valid_emojis:
            raise serializers.ValidationError(f"Invalid emoji. Choose from: {', '.join(valid_emojis)}")
        return value


class ReviewCommentReactionCreateSerializer(serializers.Serializer):
    emoji = serializers.CharField(max_length=10)

    def validate_emoji(self, value):
        valid_emojis = [choice[0] for choice in ReviewCommentReaction.EMOJI_CHOICES]
        if value not in valid_emojis:
            raise serializers.ValidationError(f"Invalid emoji. Choose from: {', '.join(valid_emojis)}")
        return value


class SongCommentReactionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SongCommentReaction
        fields = [
            'id',
            'emoji',
            'user_id',
            'user_username',
            'created_at',
        ]
        read_only_fields = fields


class SongCommentReactionCreateSerializer(serializers.Serializer):
    emoji = serializers.CharField(max_length=10)

    def validate_emoji(self, value):
        valid_emojis = [choice[0] for choice in SongCommentReaction.EMOJI_CHOICES]
        if value not in valid_emojis:
            raise serializers.ValidationError(f"Invalid emoji. Choose from: {', '.join(valid_emojis)}")
        return value


class ReactionsSummarySerializer(serializers.Serializer):
                                                            
    emoji = serializers.CharField()
    count = serializers.IntegerField()
    user_reacted = serializers.BooleanField()


class CatalogChangelogEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)

    class Meta:
        model = CatalogChangelogEvent
        fields = [
            'id',
            'kind',
            'summary',
            'diff',
            'created_at',
            'actor_username',
        ]
        read_only_fields = fields


class AlbumRatingSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AlbumRating
        fields = ["id", "album", "rating", "created_at", "user_username"]


class ArtistRatingSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ArtistRating
        fields = ["id", "artist", "rating", "created_at", "user_username"]


class SongRatingSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = SongRating
        fields = ["id", "song", "rating", "created_at", "user_username"]


class AlbumReviewSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = AlbumReview
        fields = [
            "id",
            "album",
            "title",
            "content",
            "created_at",
            "updated_at",

            "user_id",
            "user_username",

            "likes_count",
        ]

    def get_likes_count(self, obj: AlbumReview):
        count = getattr(obj, "likes_count", None)
        if count is None:
            return obj.likes.count()
        return int(count)


class PopularAlbumReviewSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True)
    album_title = serializers.CharField(source="album.title", read_only=True)
    album_slug = serializers.SlugField(source="album.slug", read_only=True)
    artist_name = serializers.CharField(source="album.artist.name", read_only=True)
    artist_slug = serializers.SlugField(source="album.artist.slug", read_only=True)
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AlbumReview
        fields = [
            "id",
            "title",
            "content",
            "created_at",

            "user_id",
            "user_username",
            "likes_count",
            "album_title",
            "album_slug",
            "artist_name",
            "artist_slug",
        ]


class ListCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = List
        fields = ["id", "name", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value: str):
        name = str(value).strip()
        if not name:
            raise serializers.ValidationError("List name is required")
        return name


class ListRenameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)

    def validate_name(self, value: str):
        name = str(value).strip()
        if not name:
            raise serializers.ValidationError("List name is required")
        return name


class ListUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False, allow_blank=False)
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_name(self, value: str):
        name = str(value).strip()
        if not name:
            raise serializers.ValidationError("List name is required")
        return name

    def validate_description(self, value: str):
                                                 
        return str(value or "")


class ListReorderSerializer(serializers.Serializer):
    item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )


class ListAlbumAddSerializer(serializers.Serializer):
    album_id = serializers.IntegerField(min_value=1)


class ListAlbumSerializer(serializers.ModelSerializer):
    album_id = serializers.IntegerField(source="album.id", read_only=True)
    album_title = serializers.CharField(source="album.title", read_only=True)
    album_slug = serializers.SlugField(source="album.slug", read_only=True)
    artist_name = serializers.CharField(source="album.artist.name", read_only=True)
    artist_slug = serializers.SlugField(source="album.artist.slug", read_only=True)
    cover_url = serializers.CharField(source="album.cover_url", read_only=True)
    release_date = serializers.DateField(source="album.release_date", read_only=True)
    my_note = serializers.SerializerMethodField()

    class Meta:
        model = ListAlbum
        fields = [
            "id",
            "album_id",
            "album_title",
            "album_slug",
            "artist_name",
            "artist_slug",
            "cover_url",
            "release_date",
            "position",
            "added_at",
            "my_note",
        ]
        read_only_fields = fields

    def get_my_note(self, obj: ListAlbum):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return ''
                                                                
        notes = list(getattr(obj, 'notes', []).all()) if hasattr(obj, 'notes') else []
        if notes:
            return str(notes[0].note or '')
        return ''


class ListSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    albums = serializers.SerializerMethodField()
    albums_count = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    collaborators = serializers.SerializerMethodField()

    class Meta:
        model = List
        fields = [
            "id",
            "name",
            "description",
            "is_public",
            "created_at",
            "updated_at",
            "user_username",
            "tags",
            "my_role",
            "collaborators",
            "albums_count",
            "albums",
        ]

    def get_albums_count(self, obj: List):
        count = getattr(obj, "albums_count", None)
        if count is None:
            return obj.albums.count()
        return int(count)

    def get_albums(self, obj: List):
                                                                       
        items = obj.list_albums.all()
        return ListAlbumSerializer(items, many=True, context=self.context).data

    def get_tags(self, obj: List):
        try:
            return [t.name for t in obj.tags.all()]
        except Exception:
            return []

    def get_my_role(self, obj: List):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return None
        if obj.user_id == user.id:
            return ListMembership.Role.OWNER
                                        
        for m in getattr(obj, 'memberships', []).all() if hasattr(obj, 'memberships') else []:
            if m.user_id == user.id:
                return m.role
        return None

    def get_collaborators(self, obj: List):
                                                                             
        out = [
            {
                'user_id': int(obj.user_id),
                'username': str(getattr(obj.user, 'username', '')),
                'role': ListMembership.Role.OWNER,
            },
        ]
        for m in getattr(obj, 'memberships', []).all() if hasattr(obj, 'memberships') else []:
            if m.user_id == obj.user_id:
                continue
            out.append(
                {
                    'user_id': int(m.user_id),
                    'username': str(getattr(m.user, 'username', '')),
                    'role': str(m.role),
                },
            )
        return ListMemberSerializer(out, many=True).data


class PublicListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    user_username = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    albums_count = serializers.IntegerField()
    likes_count = serializers.IntegerField()
    is_liked = serializers.BooleanField(required=False)

    tags = serializers.ListField(child=serializers.CharField(), required=False)


class FollowedArtistSerializer(serializers.ModelSerializer):
    artist_id = serializers.IntegerField(source='artist.id', read_only=True)
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_slug = serializers.SlugField(source='artist.slug', read_only=True)

    class Meta:
        model = ArtistFollow
        fields = [
            "id",
            "artist_id",
            "artist_name",
            "artist_slug",
            "created_at",
        ]
        read_only_fields = fields


class MyAlbumReviewSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    album_title = serializers.CharField(source="album.title", read_only=True)
    album_slug = serializers.SlugField(source="album.slug", read_only=True)
    artist_name = serializers.CharField(source="album.artist.name", read_only=True)
    artist_slug = serializers.SlugField(source="album.artist.slug", read_only=True)
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = AlbumReview
        fields = [
            "id",
            "title",
            "content",
            "created_at",
            "updated_at",
            "user_username",
            "likes_count",
            "album_title",
            "album_slug",
            "artist_name",
            "artist_slug",
        ]

    def get_likes_count(self, obj: AlbumReview):
        count = getattr(obj, "likes_count", None)
        if count is None:
            return obj.likes.count()
        return int(count)


class MyAlbumRatingSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    album_title = serializers.CharField(source="album.title", read_only=True)
    album_slug = serializers.SlugField(source="album.slug", read_only=True)
    artist_name = serializers.CharField(source="album.artist.name", read_only=True)
    artist_slug = serializers.SlugField(source="album.artist.slug", read_only=True)

    class Meta:
        model = AlbumRating
        fields = [
            "id",
            "rating",
            "created_at",
            "user_username",
            "album_title",
            "album_slug",
            "artist_name",
            "artist_slug",
        ]


class MyAlbumLikeSerializer(serializers.ModelSerializer):
    album_id = serializers.IntegerField(source="album.id", read_only=True)
    album_title = serializers.CharField(source="album.title", read_only=True)
    album_slug = serializers.SlugField(source="album.slug", read_only=True)
    artist_name = serializers.CharField(source="album.artist.name", read_only=True)
    artist_slug = serializers.SlugField(source="album.artist.slug", read_only=True)

    class Meta:
        model = AlbumLike
        fields = [
            "id",
            "created_at",
            "album_id",
            "album_title",
            "album_slug",
            "artist_name",
            "artist_slug",
        ]


class MySongRatingSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    song_title = serializers.CharField(source="song.title", read_only=True)
    song_slug = serializers.SlugField(source="song.slug", read_only=True)
    artist_name = serializers.CharField(source="song.artist.name", read_only=True)
    artist_slug = serializers.SlugField(source="song.artist.slug", read_only=True)

    class Meta:
        model = SongRating
        fields = [
            "id",
            "rating",
            "created_at",
            "user_username",
            "song_title",
            "song_slug",
            "artist_name",
            "artist_slug",
        ]


class MyAlbumListenSerializer(serializers.ModelSerializer):
    album_id = serializers.IntegerField(source="album.id", read_only=True)
    album_title = serializers.CharField(source="album.title", read_only=True)
    album_slug = serializers.SlugField(source="album.slug", read_only=True)
    artist_name = serializers.CharField(source="album.artist.name", read_only=True)
    artist_slug = serializers.SlugField(source="album.artist.slug", read_only=True)

    class Meta:
        model = AlbumListen
        fields = [
            "id",
            "listened_at",
            "listened_date",
            "album_id",
            "album_title",
            "album_slug",
            "artist_name",
            "artist_slug",
        ]


class MyWantToListenSerializer(serializers.ModelSerializer):
    album_id = serializers.IntegerField(source="album.id", read_only=True)
    album_title = serializers.CharField(source="album.title", read_only=True)
    album_slug = serializers.SlugField(source="album.slug", read_only=True)
    artist_name = serializers.CharField(source="album.artist.name", read_only=True)
    artist_slug = serializers.SlugField(source="album.artist.slug", read_only=True)

    class Meta:
        model = WantToListen
        fields = [
            "id",
            "created_at",
            "album_id",
            "album_title",
            "album_slug",
            "artist_name",
            "artist_slug",
        ]


class RatingDistributionItemSerializer(serializers.Serializer):
    stars = serializers.IntegerField(min_value=1, max_value=5)
    count = serializers.IntegerField(min_value=0)


class GenreRatedSerializer(serializers.Serializer):
    name = serializers.CharField()
    ratings = serializers.IntegerField(min_value=0)


class ProfileActivitySerializer(serializers.Serializer):
    reviews_written = serializers.IntegerField(min_value=0)
    albums_rated = serializers.IntegerField(min_value=0)
    artists_followed = serializers.IntegerField(min_value=0)
    lists_created = serializers.IntegerField(min_value=0)


class BadgeSerializer(serializers.Serializer):
    key = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    unlocked = serializers.BooleanField()


class FavoriteAlbumItemSerializer(serializers.Serializer):
    position = serializers.IntegerField(min_value=1, max_value=4)
    album_id = serializers.IntegerField(allow_null=True)
    album_title = serializers.CharField(allow_null=True)
    album_slug = serializers.CharField(allow_null=True)
    artist_name = serializers.CharField(allow_null=True)
    artist_slug = serializers.CharField(allow_null=True)
    cover_url = serializers.CharField(allow_null=True)


class FavoriteSongItemSerializer(serializers.Serializer):
    position = serializers.IntegerField(min_value=1, max_value=4)
    song_id = serializers.IntegerField(allow_null=True)
    song_title = serializers.CharField(allow_null=True)
    song_slug = serializers.CharField(allow_null=True)
    artist_name = serializers.CharField(allow_null=True)
    artist_slug = serializers.CharField(allow_null=True)
    album_title = serializers.CharField(allow_null=True)
    album_slug = serializers.CharField(allow_null=True)


class ProfileStatsSerializer(serializers.Serializer):
    favorite_genre = serializers.CharField(allow_null=True)
    favorite_artist = serializers.CharField(allow_null=True)
    total_ratings = serializers.IntegerField()
    average_rating_given = serializers.FloatField(allow_null=True)

    favorite_albums = FavoriteAlbumItemSerializer(many=True)
    favorite_songs = FavoriteSongItemSerializer(many=True)

    ratings_distribution = RatingDistributionItemSerializer(many=True)
    top_genres_rated = GenreRatedSerializer(many=True)
    activity = ProfileActivitySerializer()
    badges = BadgeSerializer(many=True)


class FavoriteAlbumsUpdateSerializer(serializers.Serializer):
                                                           
    slots = serializers.ListField(
        child=serializers.IntegerField(min_value=1, allow_null=True),
        min_length=4,
        max_length=4,
    )

    def validate_slots(self, value):
        slots = list(value or [])
        if len(slots) != 4:
            raise serializers.ValidationError("slots must have length 4")

        ids = [int(v) for v in slots if v is not None]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Album IDs must be unique")

        return slots


class FavoriteSongsUpdateSerializer(serializers.Serializer):
                                                          
    slots = serializers.ListField(
        child=serializers.IntegerField(min_value=1, allow_null=True),
        min_length=4,
        max_length=4,
    )

    def validate_slots(self, value):
        slots = list(value or [])
        if len(slots) != 4:
            raise serializers.ValidationError("slots must have length 4")

        ids = [int(v) for v in slots if v is not None]
        if len(set(ids)) != len(ids):
            raise serializers.ValidationError("Song IDs must be unique")

        return slots


class FriendRequestCreateSerializer(serializers.Serializer):
    receiver_username = serializers.CharField()


class FriendRequestActionSerializer(serializers.Serializer):
    request_id = serializers.IntegerField(min_value=1)


class FriendRequestSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    receiver_id = serializers.IntegerField(source='receiver.id', read_only=True)
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)

    class Meta:
        model = FriendRequest
        fields = [
            'id',
            'sender_id',
            'sender_username',
            'receiver_id',
            'receiver_username',
            'status',
            'created_at',
        ]
        read_only_fields = fields


class AlbumReviewLikeNotificationSerializer(serializers.ModelSerializer):
    liker_id = serializers.IntegerField(source='user.id', read_only=True)
    liker_username = serializers.CharField(source='user.username', read_only=True)

    review_id = serializers.IntegerField(source='review.id', read_only=True)
    album_id = serializers.IntegerField(source='review.album.id', read_only=True)
    album_title = serializers.CharField(source='review.album.title', read_only=True)
    album_slug = serializers.CharField(source='review.album.slug', read_only=True)
    artist_name = serializers.CharField(source='review.album.artist.name', read_only=True)
    artist_slug = serializers.CharField(source='review.album.artist.slug', read_only=True)

    class Meta:
        model = AlbumReviewLike
        fields = [
            'id',
            'created_at',
            'liker_id',
            'liker_username',
            'review_id',
            'album_id',
            'album_title',
            'album_slug',
            'artist_name',
            'artist_slug',
        ]
        read_only_fields = fields


class ReviewReplyNotificationSerializer(serializers.ModelSerializer):
    replier_id = serializers.IntegerField(source='user.id', read_only=True)
    replier_username = serializers.CharField(source='user.username', read_only=True)

    review_id = serializers.IntegerField(source='review.id', read_only=True)
    album_id = serializers.IntegerField(source='review.album.id', read_only=True)
    album_title = serializers.CharField(source='review.album.title', read_only=True)
    album_slug = serializers.CharField(source='review.album.slug', read_only=True)
    artist_name = serializers.CharField(source='review.album.artist.name', read_only=True)
    artist_slug = serializers.CharField(source='review.album.artist.slug', read_only=True)

    class Meta:
        model = ReviewComment
        fields = [
            'id',
            'created_at',
            'replier_id',
            'replier_username',
            'review_id',
            'album_id',
            'album_title',
            'album_slug',
            'artist_name',
            'artist_slug',
        ]
        read_only_fields = fields


class ReviewMentionNotificationSerializer(serializers.ModelSerializer):
    mentioner_id = serializers.IntegerField(source='comment.user.id', read_only=True)
    mentioner_username = serializers.CharField(source='comment.user.username', read_only=True)

    comment_id = serializers.IntegerField(source='comment.id', read_only=True)
    comment_content = serializers.CharField(source='comment.content', read_only=True)

    review_id = serializers.IntegerField(source='comment.review.id', read_only=True)
    album_id = serializers.IntegerField(source='comment.review.album.id', read_only=True)
    album_title = serializers.CharField(source='comment.review.album.title', read_only=True)
    album_slug = serializers.CharField(source='comment.review.album.slug', read_only=True)
    artist_name = serializers.CharField(source='comment.review.album.artist.name', read_only=True)
    artist_slug = serializers.CharField(source='comment.review.album.artist.slug', read_only=True)

    class Meta:
        model = ReviewCommentMention
        fields = [
            'id',
            'created_at',
            'mentioner_id',
            'mentioner_username',
            'comment_id',
            'comment_content',
            'review_id',
            'album_id',
            'album_title',
            'album_slug',
            'artist_name',
            'artist_slug',
        ]
        read_only_fields = fields


class SongMentionNotificationSerializer(serializers.ModelSerializer):
    mentioner_id = serializers.IntegerField(source='comment.user.id', read_only=True)
    mentioner_username = serializers.CharField(source='comment.user.username', read_only=True)

    comment_id = serializers.IntegerField(source='comment.id', read_only=True)
    comment_content = serializers.CharField(source='comment.content', read_only=True)

    song_id = serializers.IntegerField(source='comment.song.id', read_only=True)
    song_title = serializers.CharField(source='comment.song.title', read_only=True)
    song_slug = serializers.CharField(source='comment.song.slug', read_only=True)
    artist_name = serializers.CharField(source='comment.song.artist.name', read_only=True)
    artist_slug = serializers.CharField(source='comment.song.artist.slug', read_only=True)

    class Meta:
        model = SongCommentMention
        fields = [
            'id',
            'created_at',
            'mentioner_id',
            'mentioner_username',
            'comment_id',
            'comment_content',
            'song_id',
            'song_title',
            'song_slug',
            'artist_name',
            'artist_slug',
        ]
        read_only_fields = fields


class ArtistFollowNotificationSerializer(serializers.ModelSerializer):
    follower_id = serializers.IntegerField(source='user.id', read_only=True)
    follower_username = serializers.CharField(source='user.username', read_only=True)
    artist_id = serializers.IntegerField(source='artist.id', read_only=True)
    artist_name = serializers.CharField(source='artist.name', read_only=True)
    artist_slug = serializers.CharField(source='artist.slug', read_only=True)

    class Meta:
        model = ArtistFollow
        fields = [
            'id',
            'created_at',
            'follower_id',
            'follower_username',
            'artist_id',
            'artist_name',
            'artist_slug',
        ]
        read_only_fields = fields


class AlbumReleaseNotificationSerializer(serializers.Serializer):
    album_id = serializers.IntegerField()
    album_title = serializers.CharField()
    album_slug = serializers.CharField()
    artist_id = serializers.IntegerField()
    artist_name = serializers.CharField()
    artist_slug = serializers.CharField()
    release_date = serializers.DateField(allow_null=True)
    created_at = serializers.DateTimeField()
    reason = serializers.CharField()
    matched_genres = serializers.ListField(child=serializers.CharField(), required=False)


class NotificationPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreferences
        fields = [
            'notify_friend_requests',
            'notify_review_likes',
            'notify_review_replies',
            'notify_mentions',
            'notify_artist_follows',
            'notify_followed_artist_releases',
            'notify_genre_releases',
            'notify_achievement_unlocks',
            'notify_friends_activity',
            'digest_frequency',
            'digest_channel',
        ]


class AchievementUnlockNotificationSerializer(serializers.ModelSerializer):
                                              
    
    class Meta:
        model = AchievementUnlock
        fields = [
            'id',
            'achievement_code',
            'achievement_name',
            'achievement_emoji',
            'xp_awarded',
            'created_at',
        ]
        read_only_fields = fields


class UserActivitySerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)
    target_kind = serializers.SerializerMethodField()
    target_url = serializers.SerializerMethodField()

    class Meta:
        model = UserActivity
        fields = [
            'id',
            'actor_username',
            'activity_type',
            'target_kind',
            'target_url',
            'target_id',
            'target_name',
            'rating',
            'created_at',
        ]
        read_only_fields = fields

    def _target_object(self, obj):
        if not obj.target_id:
            return None

        from music.models import Album, Artist

        activity_type = str(obj.activity_type or '')
        if activity_type in {'listen_album', 'rate_album', 'review_album', 'list_add_album'}:
            return Album.objects.filter(pk=obj.target_id).only('slug').first()
        if activity_type == 'follow_artist':
            return Artist.objects.filter(pk=obj.target_id).only('slug').first()
        if activity_type == 'create_list':
            return List.objects.filter(pk=obj.target_id).only('id').first()
        return None

    def get_target_kind(self, obj):
        activity_type = str(obj.activity_type or '')
        if activity_type in {'listen_album', 'rate_album', 'review_album', 'list_add_album'}:
            return 'album'
        if activity_type == 'follow_artist':
            return 'artist'
        if activity_type == 'create_list':
            return 'list'
        return ''

    def get_target_url(self, obj):
        target = self._target_object(obj)
        if target is None:
            return ''

        activity_type = str(obj.activity_type or '')
        if activity_type == 'follow_artist':
            return f'/artists/{target.slug}'
        if activity_type == 'create_list':
            return f'/lists/public/{target.id}'
        if activity_type == 'review_album':
            return f'/albums/{target.slug}?tab=reviews'
        if activity_type in {'listen_album', 'rate_album', 'list_add_album'}:
            return f'/albums/{target.slug}'
        return ''


class ChatMessageCreateSerializer(serializers.Serializer):
    recipient_id = serializers.IntegerField(required=False)
    reply_to_id = serializers.IntegerField(required=False, allow_null=True)
    content = serializers.CharField()

    def validate_content(self, value: str):
        text = str(value or '').strip()
        if not text:
            raise serializers.ValidationError("Message cannot be empty")
        if len(text) > 1000:
            raise serializers.ValidationError("Message is too long")
        return text


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    recipient_id = serializers.IntegerField(source='recipient.id', read_only=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)
    reply_to_id = serializers.SerializerMethodField()
    reply_to_content = serializers.SerializerMethodField()
    reply_to_sender_username = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'sender_id',
            'sender_username',
            'recipient_id',
            'recipient_username',
            'reply_to_id',
            'reply_to_content',
            'reply_to_sender_username',
            'content',
            'is_read',
            'created_at',
        ]
        read_only_fields = fields

    def get_reply_to_id(self, obj):
        return obj.reply_to.id if obj.reply_to else None

    def get_reply_to_content(self, obj):
        return obj.reply_to.content if obj.reply_to else None

    def get_reply_to_sender_username(self, obj):
        return obj.reply_to.sender.username if obj.reply_to else None


class ChatTypingStatusUpdateSerializer(serializers.Serializer):
    is_typing = serializers.BooleanField()


class ChatTypingStatusSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    partner_id = serializers.IntegerField(source='partner.id', read_only=True)

    class Meta:
        model = ChatTypingStatus
        fields = [
            'user_id',
            'partner_id',
            'is_typing',
            'updated_at',
        ]
        read_only_fields = fields


class ConversationSummarySerializer(serializers.Serializer):
                                                     
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    last_message = serializers.CharField()
    last_message_at = serializers.DateTimeField()
    unread_count = serializers.IntegerField()
    is_from_current_user = serializers.BooleanField()


class CorrectionReportCreateSerializer(serializers.Serializer):
    page_url = serializers.CharField(required=False, allow_blank=True, max_length=500)
    description = serializers.CharField()

    def validate_page_url(self, value: str):
        url = str(value or '').strip()
        return url

    def validate_description(self, value: str):
        text = str(value or '').strip()
        if not text:
            raise serializers.ValidationError('Description is required')
        if len(text) > 5000:
            raise serializers.ValidationError('Description is too long')
        return text


class CorrectionReportSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = CorrectionReport
        fields = [
            'id',
            'page_url',
            'description',
            'created_at',
            'user_id',
            'username',
        ]
        read_only_fields = fields


class UserOnboardingCompleteSerializer(serializers.Serializer):
    genre_ids = serializers.ListField(child=serializers.IntegerField(), required=True)
    artist_ids = serializers.ListField(child=serializers.IntegerField(), required=True)


class UserOnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserOnboarding
        fields = [
            'is_completed',
            'completed_at',
        ]
        read_only_fields = fields
