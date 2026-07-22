from django.urls import path
from videos.views import (
    VideoListCreateView, VideoDetailView, VideoLikeView, VideoCommentView,
    VideoViewView, VideoSearchView, VideoTopView, VideoQuotaView,
)

urlpatterns = [
    path('videos/', VideoListCreateView.as_view(), name='video_list_create'),
    path('videos/search/', VideoSearchView.as_view(), name='video_search'),
    path('videos/top/', VideoTopView.as_view(), name='video_top'),
    path('videos/quota/', VideoQuotaView.as_view(), name='video_quota'),
    path('videos/<int:videoid>/', VideoDetailView.as_view(), name='video_detail'),
    path('videos/<int:videoid>/like/', VideoLikeView.as_view(), name='video_like'),
    path('videos/<int:videoid>/comments/', VideoCommentView.as_view(), name='video_comments'),
    path('videos/<int:videoid>/view/', VideoViewView.as_view(), name='video_view'),
]
