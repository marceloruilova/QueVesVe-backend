from django.http import JsonResponse

from users.constants import ACCOUNT_LOCKED_ERROR


def axes_lockout_response(request, original_response=None, credentials=None):
    """Respuesta que devuelve django-axes cuando bloquea un login (AXES_LOCKOUT_CALLABLE).
    Sin esto, axes.middleware.AxesMiddleware reemplaza la respuesta con su propia página
    HTML de bloqueo, sin importar lo que haya devuelto la vista."""
    return JsonResponse({'error': ACCOUNT_LOCKED_ERROR}, status=429)
