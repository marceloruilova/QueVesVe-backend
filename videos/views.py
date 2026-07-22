import os
import shutil
import tempfile

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated

from django.conf import settings
from django.core.files import File
from django.db.models import Q, F, Sum

from videos.models import Video, Like, Comment
from videos.serializers import VideoSerializer, CommentSerializer
from videos.media_utils import get_duration_seconds, compress_video
from videos.pagination import VideoPagination
from quevesve_back.throttles import VideoUploadRateThrottle


def _ugc_used_bytes(user):
    return Video.objects.filter(user=user, source_type='ugc').aggregate(
        total=Sum('file_size')
    )['total'] or 0


class VideoListCreateView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_throttles(self):
        if self.request.method == 'POST':
            return [VideoUploadRateThrottle()]
        return super().get_throttles()

    def get(self, request):
        qs = Video.objects.select_related('user').prefetch_related('likes').all()
        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)
        category = request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        paginator = VideoPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = VideoSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = VideoSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.data['video_file']
        client_compressed = str(request.data.get('client_compressed', '')).lower() == 'true'

        tmp_dir = tempfile.mkdtemp(prefix='ugc_upload_')
        try:
            input_path = os.path.join(tmp_dir, 'input.mp4')
            with open(input_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            duration = get_duration_seconds(input_path)
            if duration is not None and duration > settings.MAX_UGC_VIDEO_DURATION_SECONDS:
                return Response({
                    'error': 'duration_exceeded',
                    'detail': (
                        f'El video supera el límite de '
                        f'{settings.MAX_UGC_VIDEO_DURATION_SECONDS} segundos.'
                    ),
                    'max_duration_seconds': settings.MAX_UGC_VIDEO_DURATION_SECONDS,
                }, status=status.HTTP_400_BAD_REQUEST)

            used_bytes = _ugc_used_bytes(request.user)
            limit_bytes = settings.UGC_STORAGE_QUOTA_BYTES
            raw_size = os.path.getsize(input_path)
            if used_bytes + raw_size > limit_bytes:
                return self._quota_exceeded_response(used_bytes, limit_bytes)

            final_path = input_path
            if not client_compressed:
                compressed_path = os.path.join(tmp_dir, 'compressed.mp4')
                if compress_video(input_path, compressed_path):
                    final_path = compressed_path

            final_size = os.path.getsize(final_path)
            if used_bytes + final_size > limit_bytes:
                return self._quota_exceeded_response(used_bytes, limit_bytes)

            with open(final_path, 'rb') as f:
                serializer.validated_data['video_file'] = File(f, name=uploaded_file.name)
                video = serializer.save(
                    user=request.user, file_size=final_size, duration_seconds=duration,
                )

            return Response(
                VideoSerializer(video, context={'request': request}).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @staticmethod
    def _quota_exceeded_response(used_bytes, limit_bytes):
        return Response({
            'error': 'quota_exceeded',
            'detail': 'No tenés espacio suficiente disponible. Borrá videos viejos para poder subir uno nuevo.',
            'used_bytes': used_bytes,
            'limit_bytes': limit_bytes,
        }, status=status.HTTP_400_BAD_REQUEST)


class VideoQuotaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        used_bytes = _ugc_used_bytes(request.user)
        limit_bytes = settings.UGC_STORAGE_QUOTA_BYTES
        return Response({
            'used_bytes': used_bytes,
            'limit_bytes': limit_bytes,
            'remaining_bytes': max(0, limit_bytes - used_bytes),
            'used_pct': round(used_bytes / limit_bytes * 100, 1) if limit_bytes else 0,
        }, status=status.HTTP_200_OK)


class VideoDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, videoid):
        try:
            video = Video.objects.select_related('user').prefetch_related('likes').get(pk=videoid)
            serializer = VideoSerializer(video, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Video.DoesNotExist:
            return Response({'error': 'Video not found'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, videoid):
        try:
            video = Video.objects.select_related('user').prefetch_related('likes').get(pk=videoid)
        except Video.DoesNotExist:
            return Response({'error': 'Video not found'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.id != video.user_id:
            return Response(
                {'error': 'No podés editar un video que no subiste vos.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        editable_fields = {'description', 'tags', 'music'}
        data = {k: v for k, v in request.data.items() if k in editable_fields}
        serializer = VideoSerializer(video, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VideoLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, videoid):
        try:
            video = Video.objects.get(pk=videoid)
        except Video.DoesNotExist:
            return Response({'error': 'Video not found'}, status=status.HTTP_404_NOT_FOUND)
        _, created = Like.objects.get_or_create(user=request.user, video=video)
        return Response(
            {'likes': video.likes.count(), 'liked_by_user': True},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, videoid):
        try:
            video = Video.objects.get(pk=videoid)
        except Video.DoesNotExist:
            return Response({'error': 'Video not found'}, status=status.HTTP_404_NOT_FOUND)
        Like.objects.filter(user=request.user, video=video).delete()
        return Response(
            {'likes': video.likes.count(), 'liked_by_user': False},
            status=status.HTTP_200_OK,
        )


class VideoCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, videoid):
        comments = Comment.objects.filter(video_id=videoid).select_related('user')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, videoid):
        try:
            video = Video.objects.get(pk=videoid)
        except Video.DoesNotExist:
            return Response({'error': 'Video not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            comment = serializer.save(user=request.user, video=video)
            video.comments_count = video.comments.count()
            video.save(update_fields=['comments_count'])
            return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VideoViewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, videoid):
        try:
            video = Video.objects.get(pk=videoid)
        except Video.DoesNotExist:
            return Response({'error': 'Video not found'}, status=status.HTTP_404_NOT_FOUND)
        Video.objects.filter(pk=videoid).update(views_count=F('views_count') + 1)
        if request.user.id == video.user_id:
            video.refresh_from_db(fields=['views_count'])
            return Response({'views_count': video.views_count}, status=status.HTTP_200_OK)
        return Response({}, status=status.HTTP_200_OK)


class VideoSearchView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        paginator = VideoPagination()
        if not q:
            paginator.paginate_queryset(Video.objects.none(), request, view=self)
            return paginator.get_paginated_response([])
        qs = (
            Video.objects
            .select_related('user')
            .prefetch_related('likes')
            .filter(
                Q(description__icontains=q) |
                Q(tags__icontains=q) |
                Q(music__icontains=q)
            )
        )
        page = paginator.paginate_queryset(qs, request, view=self)
        serializer = VideoSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class VideoTopView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = (
            Video.objects
            .select_related('user')
            .prefetch_related('likes')
            .order_by('-views_count')[:50]
        )
        serializer = VideoSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
