from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated

from django.db.models import Q, F

from videos.models import Video, Like, Comment
from videos.serializers import VideoSerializer, CommentSerializer


class VideoListCreateView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        qs = Video.objects.select_related('user').prefetch_related('likes').all()
        user_id = request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)
        category = request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
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
        if not q:
            return Response([], status=status.HTTP_200_OK)
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
        serializer = VideoSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


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
