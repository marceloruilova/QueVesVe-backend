from django.core.mail import send_mail
from django.conf import settings


def send_verification_email(user_email: str, username: str, token_uuid: str) -> None:
    verification_url = f"{settings.BACKEND_BASE_URL}/users/verify-email/{token_uuid}/"
    subject = "Verificá tu email en QueVesVe!&"
    message = (
        f"Hola {username},\n\n"
        f"Verificá tu email haciendo clic en el siguiente enlace:\n"
        f"{verification_url}\n\n"
        f"El enlace expira en 24 horas.\n\n"
        f"Si no creaste una cuenta en QueVesVe!&, ignorá este mensaje."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=True,  # No romper el registro si el SMTP falla
    )
