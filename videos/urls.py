from django.urls import path
from videos.views import VideoListCreateView, VideoDetailView, VideoLikeView, VideoCommentView

urlpatterns = [
    path('videos/', VideoListCreateView.as_view(), name='video_list_create'),
    path('videos/<int:videoid>/', VideoDetailView.as_view(), name='video_detail'),
    path('videos/<int:videoid>/like/', VideoLikeView.as_view(), name='video_like'),
    path('videos/<int:videoid>/comments/', VideoCommentView.as_view(), name='video_comments'),
]
