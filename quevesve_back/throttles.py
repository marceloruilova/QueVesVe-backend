from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """Por IP en /users/login/ — frena credential stuffing / fuerza bruta."""
    scope = 'login'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class RegisterRateThrottle(SimpleRateThrottle):
    """Por IP en /users/register/ — frena la creación masiva de cuentas falsas."""
    scope = 'register'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class SocialAuthRateThrottle(SimpleRateThrottle):
    """Por IP en /users/social-auth/ — cada request dispara 1-2 llamadas salientes a las
    APIs de verificación de token de Google/Facebook, así que esto protege cuota externa,
    no solo CPU/DB propios."""
    scope = 'social_auth'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class VideoUploadRateThrottle(UserRateThrottle):
    """Por usuario en POST /videos/ — cada request corre compresión ffmpeg sincrónica,
    así que este límite acota costo de CPU, no solo cantidad de requests."""
    scope = 'video_upload'
