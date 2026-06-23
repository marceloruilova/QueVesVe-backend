from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from videos.models import Video
from .models import ContentReport
from .serializers import ContentReportSerializer, CopyrightReportSerializer


class ReportVideoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, videoid):
        try:
            video = Video.objects.get(pk=videoid)
        except Video.DoesNotExist:
            return Response({'error': 'Video no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if ContentReport.objects.filter(reporter=request.user, video=video).exists():
            return Response(
                {'error': 'Ya reportaste este video.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ContentReportSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(reporter=request.user, video=video)
            return Response(
                {'message': 'Reporte enviado. Lo revisaremos pronto.'},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CopyrightReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CopyrightReportSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Denuncia de copyright recibida. Te contactaremos pronto.'},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
