import re
import random

import requests as http_requests
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from users.models.custom_user_models import CustomUser
from users.serializers import CustomUserSerializer
from utils.request_utils import get_client_ip
from quevesve_back.throttles import SocialAuthRateThrottle


def _generate_unique_username(email_prefix: str) -> str:
    base = re.sub(r'[^a-zA-Z0-9_]', '', email_prefix)[:28] or 'user'
    candidate = base
    while CustomUser.objects.filter(username=candidate).exists():
        candidate = f"{base}{random.randint(1, 9999)}"
    return candidate


def _get_or_create_social_user(email: str, name: str) -> CustomUser:
    user = CustomUser.objects.filter(email=email).first()
    if user:
        return user
    username = _generate_unique_username(email.split('@')[0])
    parts = name.split(' ', 1) if name else ['', '']
    user = CustomUser(
        username=username,
        email=email,
        first_name=parts[0],
        last_name=parts[1] if len(parts) > 1 else '',
        email_verified=True,
    )
    user.set_unusable_password()
    user.save()
    return user


class SocialAuthAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [SocialAuthRateThrottle]

    def post(self, request) -> Response:
        provider = request.data.get('provider')
        token = request.data.get('token')

        if not provider or not token:
            return Response(
                {'error': 'provider y token son requeridos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if provider == 'google':
                user_info = self._verify_google(token)
            elif provider == 'facebook':
                user_info = self._verify_facebook(token)
            else:
                return Response(
                    {'error': 'Proveedor no válido.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        user = _get_or_create_social_user(user_info['email'], user_info.get('name', ''))

        from django.utils import timezone
        from users.models.login_log_model import LoginLog
        LoginLog.objects.create(
            user=user,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            method=provider,
        )
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': CustomUserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _verify_google(token: str) -> dict:
        if not settings.GOOGLE_OAUTH_CLIENT_IDS:
            raise ValueError('El login con Google no está configurado en el servidor.')

        tokeninfo_resp = http_requests.get(
            'https://www.googleapis.com/oauth2/v3/tokeninfo',
            params={'access_token': token},
            timeout=10,
        )
        if not tokeninfo_resp.ok:
            raise ValueError('Token de Google inválido o expirado.')
        tokeninfo = tokeninfo_resp.json()
        audience = tokeninfo.get('aud') or tokeninfo.get('azp')
        if audience not in settings.GOOGLE_OAUTH_CLIENT_IDS:
            raise ValueError('El token de Google no fue emitido para esta aplicación.')

        resp = http_requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {token}'},
            timeout=10,
        )
        if not resp.ok:
            raise ValueError('Token de Google inválido o expirado.')
        data = resp.json()
        if not data.get('email'):
            raise ValueError('Google no devolvió un email. Verificá los permisos de tu cuenta.')
        return {'email': data['email'], 'name': data.get('name', '')}

    @staticmethod
    def _verify_facebook(token: str) -> dict:
        if not settings.FACEBOOK_APP_ID:
            raise ValueError('El login con Facebook no está configurado en el servidor.')

        app_resp = http_requests.get(
            'https://graph.facebook.com/app',
            params={'access_token': token},
            timeout=10,
        )
        if not app_resp.ok or 'error' in app_resp.json():
            raise ValueError('Token de Facebook inválido o expirado.')
        if app_resp.json().get('id') != settings.FACEBOOK_APP_ID:
            raise ValueError('El token de Facebook no fue emitido para esta aplicación.')

        resp = http_requests.get(
            'https://graph.facebook.com/me',
            params={'fields': 'id,name,email', 'access_token': token},
            timeout=10,
        )
        if not resp.ok or 'error' in resp.json():
            raise ValueError('Token de Facebook inválido o expirado.')
        data = resp.json()
        if not data.get('email'):
            raise ValueError(
                'Facebook no devolvió un email. '
                'Asegurate de que tu email sea público en tu cuenta de Facebook.'
            )
        return {'email': data['email'], 'name': data.get('name', '')}
