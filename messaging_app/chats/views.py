# chats/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Max, Prefetch
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Conversation, Message, ConversationParticipant, MessageReadStatus
from .serializers import (
    ConversationSerializer, ConversationListSerializer, ConversationCreateSerializer,
    MessageSerializer, MessageCreateSerializer, MessageMarkAsReadSerializer,
    UserSerializer, UserSimpleSerializer
)

User = get_user_model()


class MessagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MessagePagination

    def get_queryset(self):
        """
        Return conversations where the current user is a participant
        """
        return Conversation.objects.filter(
            participants=self.request.user,
            is_active=True
        ).prefetch_related(
            'participants',
            'created_by',
            'participant_details__user',
            Prefetch('messages', queryset=Message.objects.select_related('sender'))
        ).distinct().order_by('-updated_at')

    def get_serializer_class(self):
        """
        Use different serializers for different actions
        """
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'create':
            return ConversationCreateSerializer
        return ConversationSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a new conversation
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if it's a private conversation and if one already exists
        if serializer.validated_data.get('conversation_type') == 'private':
            participant_ids = serializer.validated_data.get('participant_ids', [])
            if len(participant_ids) == 1:
                # Check if private conversation already exists
                existing_conversation = Conversation.objects.filter(
                    conversation_type='private',
                    participants=request.user
                ).filter(
                    participants__id=participant_ids[0]
                ).first()
                
                if existing_conversation:
                    return Response(
                        ConversationSerializer(existing_conversation, context={'request': request}).data,
                        status=status.HTTP_200_OK
                    )
        
        conversation = serializer.save()
        return Response(
            ConversationSerializer(conversation, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """
        Add a participant to a conversation
        """
        conversation = self.get_object()
        
        # Check if user has permission to add participants
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user
        ).first()
        
        if not participant or participant.role not in ['admin', 'owner']:
            return Response(
                {'error': 'You do not have permission to add participants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is already a participant
        if conversation.participants.filter(id=user_id).exists():
            return Response(
                {'error': 'User is already a participant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add participant
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=user,
            role='member'
        )
        
        return Response(
            ConversationSerializer(conversation, context={'request': request}).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """
        Remove a participant from a conversation
        """
        conversation = self.get_object()
        
        # Check if user has permission to remove participants
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user
        ).first()
        
        if not participant or participant.role not in ['admin', 'owner']:
            return Response(
                {'error': 'You do not have permission to remove participants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant_to_remove = ConversationParticipant.objects.get(
                conversation=conversation,
                user__id=user_id
            )
        except ConversationParticipant.DoesNotExist:
            return Response(
                {'error': 'Participant not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Cannot remove owner
        if participant_to_remove.role == 'owner':
            return Response(
                {'error': 'Cannot remove conversation owner'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant_to_remove.delete()
        
        return Response(
            ConversationSerializer(conversation, context={'request': request}).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def leave_conversation(self, request, pk=None):
        """
        Leave a conversation
        """
        conversation = self.get_object()
        
        try:
            participant = ConversationParticipant.objects.get(
                conversation=conversation,
                user=request.user
            )
        except ConversationParticipant.DoesNotExist:
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if participant.role == 'owner':
            return Response(
                {'error': 'Owner cannot leave conversation. Transfer ownership first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant.delete()
        
        return Response(
            {'message': 'Successfully left conversation'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark all messages in a conversation as read
        """
        conversation = self.get_object()
        
        # Update participant's last_read_at
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user=request.user
        ).first()
        
        if participant:
            participant.last_read_at = timezone.now()
            participant.save()
        
        return Response(
            {'message': 'Conversation marked as read'},
            status=status.HTTP_200_OK
        )


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MessagePagination

    def get_queryset(self):
        """
        Return messages from conversations where the current user is a participant
        """
        conversation_id = self.request.query_params.get('conversation_id')
        
        base_queryset = Message.objects.select_related(
            'sender', 'conversation', 'reply_to__sender'
        ).prefetch_related(
            'read_statuses__user'
        ).filter(
            conversation__participants=self.request.user,
            is_deleted=False
        )
        
        if conversation_id:
            base_queryset = base_queryset.filter(conversation_id=conversation_id)
        
        return base_queryset.order_by('-created_at')

    def get_serializer_class(self):
        """
        Use different serializers for different actions
        """
        if self.action == 'create':
            return MessageCreateSerializer
        elif self.action == 'mark_as_read':
            return MessageMarkAsReadSerializer
        return MessageSerializer

    def create(self, request, *args, **kwargs):
        """
        Send a new message
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        conversation_id = serializer.validated_data.get('conversation')
        
        # Check if user is a participant in the conversation
        if not Conversation.objects.filter(
            id=conversation_id.id,
            participants=request.user
        ).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message = serializer.save()
        
        # Return full message details
        return Response(
            MessageSerializer(message, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """
        Update a message (edit functionality)
        """
        message = self.get_object()
        
        # Check if user is the sender
        if message.sender != request.user:
            return Response(
                {'error': 'You can only edit your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow editing content
        allowed_fields = ['content']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = self.get_serializer(message, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a message (soft delete)
        """
        message = self.get_object()
        
        # Check if user is the sender
        if message.sender != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save()
        
        return Response(
            {'message': 'Message deleted successfully'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """
        Mark messages as read
        """
        serializer = MessageMarkAsReadSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {'message': 'Messages marked as read'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """
        Get replies to a specific message
        """
        message = self.get_object()
        replies = message.replies.filter(is_deleted=False).select_related('sender')
        
        serializer = MessageSerializer(replies, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search messages
        """
        query = request.query_params.get('q', '')
        conversation_id = request.query_params.get('conversation_id')
        
        if not query:
            return Response(
                {'error': 'Search query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(
            content__icontains=query
        )
        
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user operations (read-only for now)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get current user's profile
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search users
        """
        query = request.query_params.get('q', '')
        
        if not query:
            return Response(
                {'error': 'Search query is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id)[:10]  # Limit to 10 results
        
        serializer = UserSimpleSerializer(users, many=True)
        return Response(serializer.data)