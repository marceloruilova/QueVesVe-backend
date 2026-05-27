from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.http import HttpRequest

from users.models.custom_user_models import CustomUser
from users.models.follow_model import Follow
from users.constants import USER_WITH_ID_NOT_FOUND, USER_NOT_FOUND_MESSAGE
from utils import logger_config

logger = logger_config.configure_logger()


class FollowUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest, userid: int) -> Response:
        if request.user.id == userid:
            return Response(
                {'error': 'No puedes seguirte a ti mismo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            target = CustomUser.objects.get(pk=userid)
        except CustomUser.DoesNotExist:
            logger.error(USER_WITH_ID_NOT_FOUND, userid)
            return Response({'error': USER_NOT_FOUND_MESSAGE}, status=status.HTTP_404_NOT_FOUND)

        _, created = Follow.objects.get_or_create(
            follower=request.user, following=target
        )
        if not created:
            return Response({'detail': 'Ya sigues a este usuario.'}, status=status.HTTP_200_OK)

        return Response(
            {
                'detail': f'Ahora sigues a @{target.username}.',
                'followers_count': target.followers.count(),
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request: HttpRequest, userid: int) -> Response:
        try:
            target = CustomUser.objects.get(pk=userid)
        except CustomUser.DoesNotExist:
            logger.error(USER_WITH_ID_NOT_FOUND, userid)
            return Response({'error': USER_NOT_FOUND_MESSAGE}, status=status.HTTP_404_NOT_FOUND)

        deleted, _ = Follow.objects.filter(
            follower=request.user, following=target
        ).delete()

        if not deleted:
            return Response({'detail': 'No seguías a este usuario.'}, status=status.HTTP_200_OK)

        return Response(
            {
                'detail': f'Dejaste de seguir a @{target.username}.',
                'followers_count': target.followers.count(),
            },
            status=status.HTTP_200_OK,
        )
