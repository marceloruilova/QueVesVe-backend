from django.conf import settings
from django.db import models


LOGIN_METHODS = [
    ('password', 'Contraseña'),
    ('google', 'Google'),
    ('facebook', 'Facebook'),
]


class LoginLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='login_logs',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    method = models.CharField(max_length=20, choices=LOGIN_METHODS, default='password')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Log de acceso'
        verbose_name_plural = 'Logs de acceso'

    def __str__(self):
        return f'{self.user.username} — {self.method} — {self.created_at:%Y-%m-%d %H:%M}'
