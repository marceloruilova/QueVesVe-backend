from django.urls import path
from videos.views import VideoListCreateView, VideoDetailView

urlpatterns = [
    path('videos/', VideoListCreateView.as_view(), name='video_list_create'),
    path('videos/<int:videoid>/', VideoDetailView.as_view(), name='video_detail'),
]
