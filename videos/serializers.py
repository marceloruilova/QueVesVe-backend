from rest_framework import serializers
from videos.models import Video


class VideoSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    likes = serializers.IntegerField(source='likes_count', read_only=True)
    comments = serializers.IntegerField(source='comments_count', read_only=True)
    uri = serializers.SerializerMethodField()
    video_file = serializers.FileField(write_only=True)

    def get_uri(self, obj):
        request = self.context.get('request')
        if obj.video_file and request:
            return request.build_absolute_uri(obj.video_file.url)
        return None

    class Meta:
        model = Video
        fields = [
            'id', 'video_file', 'username', 'profile_picture',
            'description', 'tags', 'music', 'likes', 'comments', 'uri', 'created_at',
        ]
        read_only_fields = ['likes', 'comments', 'username', 'profile_picture', 'uri', 'created_at']
        extra_kwargs = {'video_file': {'write_only': True}}
