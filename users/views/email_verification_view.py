import datetime

from django.http import HttpResponse
from django.utils import timezone
from django.views import View

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models.email_verification_token_model import EmailVerificationToken
from users.services.email_service import send_verification_email


class VerifyEmailAPIView(View):
    def get(self, request, token):
        try:
            record = EmailVerificationToken.objects.select_related('user').get(token=token)
        except EmailVerificationToken.DoesNotExist:
            return HttpResponse(
                "<h2 style='font-family:sans-serif;text-align:center;margin-top:60px'>"
                "Enlace inválido o ya utilizado.</h2>",
                status=400,
                content_type="text/html; charset=utf-8",
            )

        if record.is_expired():
            record.delete()
            return HttpResponse(
                "<h2 style='font-family:sans-serif;text-align:center;margin-top:60px'>"
                "El enlace expiró. Solicitá uno nuevo desde la app.</h2>",
                status=410,
                content_type="text/html; charset=utf-8",
            )

        user = record.user
        user.email_verified = True
        user.save(update_fields=['email_verified'])
        record.delete()

        return HttpResponse(
            "<h2 style='font-family:sans-serif;text-align:center;margin-top:60px;color:#16a34a'>"
            "¡Email verificado correctamente!</h2>"
            "<p style='font-family:sans-serif;text-align:center;color:#555'>"
            "Ya podés cerrar esta ventana y volver a la app.</p>",
            status=200,
            content_type="text/html; charset=utf-8",
        )


class ResendVerificationEmailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.email_verified:
            return Response(
                {'detail': 'Tu email ya está verificado.'},
                status=status.HTTP_200_OK,
            )

        try:
            existing = user.email_verification_token
            age = timezone.now() - existing.created_at
            if age < datetime.timedelta(minutes=5):
                remaining = 300 - int(age.total_seconds())
                return Response(
                    {'detail': f'Esperá {remaining} segundos antes de reenviar.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            existing.delete()
        except EmailVerificationToken.DoesNotExist:
            pass

        token = EmailVerificationToken.objects.create(user=user)
        send_verification_email(user.email, user.username, str(token.token))

        return Response(
            {'detail': 'Email de verificación reenviado.'},
            status=status.HTTP_200_OK,
        )
