from typing import Any, Dict

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError


User = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    is_adult = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'bio', 'profile_picture',
            'professional_title', 'professional_institution',
            'cedula', 'senescyt_number',
            'senescyt_verified', 'senescyt_verified_name', 'senescyt_verified_at',
            'birth_date', 'is_adult',
            'email_verified',
            'followers_count', 'following_count', 'is_following',
        ]
        extra_kwargs: Dict[str, Dict[str, Any]] = {
            'password': {'write_only': True},
            'cedula': {'write_only': True},
            'senescyt_verified': {'read_only': True},
            'senescyt_verified_name': {'read_only': True},
            'senescyt_verified_at': {'read_only': True},
            'is_adult': {'read_only': True},
            'email_verified': {'read_only': True},
        }

    def get_followers_count(self, obj) -> int:
        return obj.followers.count()

    def get_following_count(self, obj) -> int:
        return obj.following.count()

    def get_is_adult(self, obj) -> bool:
        return obj.is_adult

    def get_is_following(self, obj) -> bool:
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.followers.filter(follower=request.user).exists()
        return False

    def validate_password(self, value: str) -> str:
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def create(self, validated_data: Dict[str, Any]) -> User:
        user: User = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        user.bio = validated_data.get('bio', '')
        user.profile_picture = validated_data.get('profile_picture', None)
        user.save()
        return user
