from django.urls import path
from .views import ReportVideoView, CopyrightReportView

urlpatterns = [
    path('videos/<int:videoid>/report/', ReportVideoView.as_view(), name='report_video'),
    path('reports/copyright/', CopyrightReportView.as_view(), name='report_copyright'),
]
