from rest_framework import serializers
from videos.models import Video, Comment


class VideoSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    likes = serializers.SerializerMethodField()
    comments = serializers.IntegerField(source='comments_count', read_only=True)
    liked_by_user = serializers.SerializerMethodField()
    uri = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    video_file = serializers.FileField(write_only=True)

    def get_likes(self, obj):
        return obj.likes.count()

    def get_liked_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
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
            'id', 'video_file', 'username', 'profile_picture',
            'description', 'tags', 'music', 'likes', 'comments',
            'liked_by_user', 'uri', 'thumbnail_url', 'created_at',
        ]
        read_only_fields = [
            'likes', 'comments', 'liked_by_user', 'username',
            'profile_picture', 'uri', 'thumbnail_url', 'created_at',
        ]
        extra_kwargs = {'video_file': {'write_only': True}}


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'username', 'text', 'created_at']
        read_only_fields = ['id', 'username', 'created_at']
