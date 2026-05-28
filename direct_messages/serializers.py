from rest_framework import serializers
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source='sender.id', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'sender_username', 'text', 'created_at', 'is_read']
        read_only_fields = ['id', 'sender_id', 'sender_username', 'created_at', 'is_read']


class ConversationSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'other_participant', 'last_message', 'unread_count', 'updated_at']

    def get_other_participant(self, obj):
        request = self.context.get('request')
        other = obj.participants.exclude(id=request.user.id).first()
        if not other:
            return None
        profile_picture = None
        if other.profile_picture:
            profile_picture = request.build_absolute_uri(other.profile_picture.url)
        return {
            'id': other.id,
            'username': other.username,
            'profile_picture': profile_picture,
        }

    def get_last_message(self, obj):
        msg = obj.messages.last()
        if not msg:
            return None
        return {
            'text': msg.text,
            'sender_id': msg.sender_id,
            'created_at': msg.created_at,
        }

    def get_unread_count(self, obj):
        request = self.context.get('request')
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
