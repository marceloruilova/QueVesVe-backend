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

_BASE_PAGE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} · QueVesVe!&amp;</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #f5f5f5;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
    }}
    .card {{
      background: #fff;
      border-radius: 10px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.10);
      max-width: 440px;
      width: 100%;
      overflow: hidden;
    }}
    .header {{
      background: #F5A623;
      padding: 24px 32px;
      text-align: center;
    }}
    .header h1 {{
      color: #fff;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.3px;
    }}
    .body {{
      padding: 36px 32px 28px;
      text-align: center;
    }}
    .icon {{
      font-size: 48px;
      margin-bottom: 16px;
      line-height: 1;
    }}
    .body h2 {{
      font-size: 20px;
      font-weight: 700;
      color: #111;
      margin-bottom: 12px;
    }}
    .body p {{
      font-size: 15px;
      color: #555;
      line-height: 1.6;
    }}
    .footer {{
      padding: 16px 32px;
      border-top: 1px solid #eee;
      text-align: center;
    }}
    .footer p {{
      font-size: 12px;
      color: #aaa;
    }}
    .footer a {{
      color: #F5A623;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>QueVesVe!&amp;</h1>
    </div>
    <div class="body">
      <div class="icon">{icon}</div>
      <h2>{heading}</h2>
      <p>{body_text}</p>
    </div>
    <div class="footer">
      <p>&copy; 2025 QueVesVe!&amp; &nbsp;&middot;&nbsp; <a href="mailto:soporte@quevesve.app">Soporte</a></p>
    </div>
  </div>
</body>
</html>"""


def _render(title, icon, heading, body_text, http_status):
    html = _BASE_PAGE.format(
        title=title,
        icon=icon,
        heading=heading,
        body_text=body_text,
    )
    return HttpResponse(html, status=http_status, content_type="text/html; charset=utf-8")


class VerifyEmailAPIView(View):
    def get(self, request, token):
        try:
            record = EmailVerificationToken.objects.select_related('user').get(token=token)
        except EmailVerificationToken.DoesNotExist:
            return _render(
                title="Enlace inválido",
                icon="✗",
                heading="Enlace inválido",
                body_text=(
                    "Este enlace ya fue utilizado o no es válido.<br><br>"
                    "Pedí uno nuevo desde tu perfil en la app."
                ),
                http_status=400,
            )

        if record.is_expired():
            record.delete()
            return _render(
                title="Enlace expirado",
                icon="⏱",
                heading="El enlace expiró",
                body_text=(
                    "Los enlaces de verificación duran 24 horas.<br><br>"
                    "Abrí la app y pedí uno nuevo desde tu perfil."
                ),
                http_status=410,
            )

        user = record.user
        user.email_verified = True
        user.save(update_fields=['email_verified'])
        record.delete()

        return _render(
            title="Email verificado",
            icon="✓",
            heading="¡Email verificado!",
            body_text=(
                "Tu cuenta está confirmada. Ya podés cerrar esta<br>"
                "ventana y volver a la app."
            ),
            http_status=200,
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
