from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    bio = models.TextField(_("bio"), max_length=500, blank=True)
    profile_picture = models.ImageField(
        _("profile picture"), upload_to='profile_pictures/', null=True, blank=True)

    # Perfil profesional
    professional_title = models.CharField(max_length=200, blank=True)
    professional_institution = models.CharField(max_length=300, blank=True)

    # Verificación SENESCYT Ecuador
    cedula = models.CharField(max_length=10, blank=True)
    senescyt_number = models.CharField(max_length=50, blank=True)
    senescyt_verified = models.BooleanField(default=False)
    senescyt_verified_name = models.CharField(max_length=300, blank=True)
    senescyt_verified_at = models.DateTimeField(null=True, blank=True)

    # Edad
    birth_date = models.DateField(null=True, blank=True)

    @property
    def is_adult(self):
        if not self.birth_date:
            return False
        from django.utils import timezone
        today = timezone.now().date()
        age = today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
        return age >= 18
