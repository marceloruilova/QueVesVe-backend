from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from users.models.custom_user_models import CustomUser
from users.serializers import CustomUserSerializer

SEARCH_LIMIT = 10


class UserSearchView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        try:
            offset = max(0, int(request.query_params.get('offset', 0)))
        except (ValueError, TypeError):
            offset = 0

        qs = CustomUser.objects.order_by('username')

        if request.user.is_authenticated:
            qs = qs.exclude(id=request.user.id)

        if q:
            qs = qs.filter(username__icontains=q)

        page = qs[offset: offset + SEARCH_LIMIT]
        serializer = CustomUserSerializer(page, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
