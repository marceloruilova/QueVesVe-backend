from django.urls import path
from .views import ConversationListView, MessageListView, MarkConversationReadView

urlpatterns = [
    path('messages/conversations/', ConversationListView.as_view(), name='conversation_list'),
    path('messages/conversations/<int:conversation_id>/messages/', MessageListView.as_view(), name='message_list'),
    path('messages/conversations/<int:conversation_id>/read/', MarkConversationReadView.as_view(), name='mark_read'),
]
