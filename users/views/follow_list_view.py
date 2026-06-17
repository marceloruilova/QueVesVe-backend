from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.http import HttpRequest

from users.models.custom_user_models import CustomUser
from users.serializers import CustomUserSerializer
from utils import logger_config

logger = logger_config.configure_logger()


class FollowListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest, userid: int) -> Response:
        if request.user.id != userid:
            return Response(
                {'error': 'No tenés permiso para ver esta lista.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        list_type = request.query_params.get('type', 'followers')

        try:
            target = CustomUser.objects.get(pk=userid)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if list_type == 'following':
            users = CustomUser.objects.filter(followers__follower=target)
        else:
            users = CustomUser.objects.filter(following__following=target)

        serializer = CustomUserSerializer(users, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
