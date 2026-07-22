from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from django.http import HttpRequest
from rest_framework.exceptions import ValidationError
from django.contrib.auth import authenticate

from utils import logger_config
from utils.request_utils import get_client_ip
from users.constants import WRONG_CREDENTIALS_ERROR, FAILED_LOGIN_ATTEMPT, MISSING_FIELD_ERROR
from quevesve_back.throttles import LoginRateThrottle

logger = logger_config.configure_logger()


class LoginUserAPIView(APIView):
    """
    API view for user login.

    This view handles the POST request for user login. It expects the 'username' and 'password'
    fields in the request data.

    Methods:
    - post(request: HttpRequest) -> Response: Handles the POST request for user login.

    Returns:
    - Response: The HTTP response object containing the refresh and access tokens if
      the login is successful, or an error message if the provided credentials are invalid.
    """

    throttle_classes = [LoginRateThrottle]

    def post(self, request: HttpRequest) -> Response:
        """
        Handle the HTTP POST request to authenticate a user.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            Response: The HTTP response object containing the authentication tokens if successful,
            or an error message if the credentials are invalid.
        """
        try:
            username = request.data['username']
            password = request.data['password']
        except KeyError as e:
            raise ValidationError(f'{MISSING_FIELD_ERROR} {e.args[0]}') from e

        user = authenticate(username=username, password=password)

        if not user:
            logger.warning(FAILED_LOGIN_ATTEMPT, username)
            return Response({"error": WRONG_CREDENTIALS_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        from users.models.login_log_model import LoginLog
        LoginLog.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            method='password',
        )
        # JWT no llama a django.contrib.auth.login(), así que actualizamos last_login manualmente
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)
