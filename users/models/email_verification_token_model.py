import uuid
import datetime

from django.db import models
from django.conf import settings
from django.utils import timezone


class EmailVerificationToken(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='email_verification_token',
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self) -> bool:
        return timezone.now() > self.created_at + datetime.timedelta(hours=24)

    def __str__(self):
        return f"VerificationToken({self.user.username}, expired={self.is_expired()})"
