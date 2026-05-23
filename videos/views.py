from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated

from videos.models import Video, Like, Comment
from videos.serializers import VideoSerializer, CommentSerializer


class VideoListCreateView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = Video.objects.select_related('user').prefetch_related('likes').all()
        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)
        serializer = VideoSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = VideoSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VideoDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, videoid):
        try:
            video = Video.objects.select_related('user').prefetch_related('likes').get(pk=videoid)
            serializer = VideoSerializer(video, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Video.DoesNotExist:
            return Response({'error': 'Video not found'}, status=status.HTTP_404_NOT_FOUND)


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
