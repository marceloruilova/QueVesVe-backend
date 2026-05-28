from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

User = get_user_model()


class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = request.user.conversations.prefetch_related('participants', 'messages')
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        recipient_id = request.data.get('recipient_id')
        if not recipient_id:
            return Response({'error': 'recipient_id es requerido.'}, status=status.HTTP_400_BAD_REQUEST)

        if int(recipient_id) == request.user.id:
            return Response({'error': 'No podés enviarte mensajes a vos mismo.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        existing = request.user.conversations.filter(participants=recipient)
        if existing.exists():
            conversation = existing.first()
        else:
            conversation = Conversation.objects.create()
            conversation.participants.add(request.user, recipient)

        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        try:
            conversation = request.user.conversations.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversación no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        messages = conversation.messages.all()
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request, conversation_id):
        try:
            conversation = request.user.conversations.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversación no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        text = request.data.get('text', '').strip()
        if not text:
            return Response({'error': 'El mensaje no puede estar vacío.'}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(conversation=conversation, sender=request.user, text=text)
        conversation.save()  # updates updated_at for ordering

        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MarkConversationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        try:
            conversation = request.user.conversations.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversación no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        return Response({'status': 'ok'})
