from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.http import HttpRequest

from users.models.custom_user_models import CustomUser
from users.services.senescyt_service import verify_senescyt
from utils import logger_config

logger = logger_config.configure_logger()

ERROR_MESSAGES = {
    "SENESCYT_NOT_FOUND": "No se encontró ningún título con ese número de registro y cédula.",
    "SENESCYT_TIMEOUT": "El servicio SENESCYT tardó demasiado. Intentá de nuevo más tarde.",
    "SENESCYT_UNAVAILABLE": "El servicio SENESCYT no está disponible en este momento.",
    "SENESCYT_HTTP_ERROR": "Error al comunicarse con SENESCYT. Intentá de nuevo.",
    "SENESCYT_PARSE_ERROR": "No se pudo leer la respuesta de SENESCYT.",
    "SENESCYT_UNKNOWN_ERROR": "Error inesperado al verificar con SENESCYT.",
}


class VerifySenescytAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: HttpRequest, userid: int) -> Response:
        if request.user.id != userid:
            return Response(
                {'error': 'Solo puedes verificar tu propio título.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        cedula = request.data.get('cedula', '').strip()
        senescyt_number = request.data.get('numeroRegistroSenescyt', '').strip()

        if not cedula or not senescyt_number:
            return Response(
                {'error': 'Se requieren cedula y numeroRegistroSenescyt.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = verify_senescyt(cedula, senescyt_number)

        if not result['verified']:
            error_code = result.get('error', 'SENESCYT_UNKNOWN_ERROR')
            return Response(
                {'error': ERROR_MESSAGES.get(error_code, error_code)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            user = CustomUser.objects.get(pk=userid)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        user.cedula = cedula
        user.senescyt_number = senescyt_number
        user.senescyt_verified = True
        user.senescyt_verified_name = result['name']
        user.senescyt_verified_at = timezone.now()
        if result.get('title') and not user.professional_title:
            user.professional_title = result['title']
        if result.get('institution') and not user.professional_institution:
            user.professional_institution = result['institution']
        user.save()

        return Response(
            {
                'detail': 'Título verificado correctamente.',
                'verified_name': result['name'],
                'title': result['title'],
                'institution': result['institution'],
            },
            status=status.HTTP_200_OK,
        )
