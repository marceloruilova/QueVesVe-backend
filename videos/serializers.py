from rest_framework import serializers
from videos.models import Video, Comment


class VideoSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    likes = serializers.SerializerMethodField()
    comments = serializers.IntegerField(source='comments_count', read_only=True)
    liked_by_user = serializers.SerializerMethodField()
    uri = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    video_file = serializers.FileField(write_only=True)

    def get_likes(self, obj):
        # usa el prefetch cache en lugar de lanzar COUNT query por cada video
        return len(obj.likes.all())

    def get_liked_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            uid = request.user.id
            # itera sobre el prefetch cache, sin query adicional
            return any(like.user_id == uid for like in obj.likes.all())
        return False

    def get_uri(self, obj):
        request = self.context.get('request')
        if obj.video_file and request:
            return request.build_absolute_uri(obj.video_file.url)
        return None

    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if obj.thumbnail and request:
            return request.build_absolute_uri(obj.thumbnail.url)
        return None

    class Meta:
        model = Video
        fields = [
            'id', 'video_file', 'user_id', 'username', 'profile_picture',
            'description', 'tags', 'music', 'likes', 'comments',
            'liked_by_user', 'uri', 'thumbnail_url', 'created_at',
        ]
        read_only_fields = [
            'likes', 'comments', 'liked_by_user', 'user_id', 'username',
            'profile_picture', 'uri', 'thumbnail_url', 'created_at',
        ]
        extra_kwargs = {'video_file': {'write_only': True}}


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'username', 'text', 'created_at']
        read_only_fields = ['id', 'username', 'created_at']
