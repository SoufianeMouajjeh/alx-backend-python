from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from .models import Conversation, Message, User
from .serializers import ConversationSerializer, MessageSerializer, UserSerializer
from .permissions import IsParticipantOfConversation
from rest_framework import status
from .pagination import MessagePagination
from .filters import MessageFilter

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsParticipantOfConversation]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['participants', 'created_at']
    search_fields = ['participants__username', 'participants__email']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)

    def perform_create(self, serializer):
        conversation = serializer.save()
        # Add the creator as a participant
        conversation.participants.add(self.request.user)
        
        # Add other participants from the request data
        participants = self.request.data.get('participants', [])
        if participants:
            # Support both user IDs and emails
            for participant in participants:
                try:
                    if '@' in str(participant):  # It's an email
                        user = User.objects.get(email=participant)
                    else:  # It's a user ID
                        user = User.objects.get(user_id=participant)
                    conversation.participants.add(user)
                except User.DoesNotExist:
                    continue

    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Ajouter un participant à la conversation"""
        conversation = self.get_object()
        participant_email = request.data.get('email')
        
        if not participant_email:
            return Response(
                {'error': 'Email du participant requis'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=participant_email)
            conversation.participants.add(user)
            return Response(
                {'message': 'Participant ajouté avec succès'}, 
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'Utilisateur non trouvé'}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def leave_conversation(self, request, pk=None):
        """Quitter une conversation"""
        conversation = self.get_object()
        conversation.participants.remove(request.user)
        return Response(
            {'message': 'Vous avez quitté la conversation'}, 
            status=status.HTTP_200_OK
        )

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsParticipantOfConversation]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sender', 'is_read', 'sent_at']
    search_fields = ['message_body', 'sender__username']
    ordering_fields = ['sent_at']
    ordering = ['sent_at']
    pagination_class = MessagePagination
    filterset_class = MessageFilter

    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_pk')
        if conversation_id:
            # Vérifier que l'utilisateur est participant à la conversation
            conversation = get_object_or_404(Conversation, conversation_id=conversation_id)
            if not conversation.participants.filter(user_id=self.request.user.user_id).exists():
                raise PermissionDenied("Vous n'êtes pas participant à cette conversation")
            
            return Message.objects.filter(conversation_id=conversation_id)
        
        # Si pas de conversation spécifique, retourner tous les messages des conversations de l'utilisateur
        return Message.objects.filter(
            conversation__participants=self.request.user
        )

    def perform_create(self, serializer):
        conversation_id = self.kwargs.get('conversation_pk')
        if not conversation_id:
            raise PermissionDenied("ID de conversation requis")
            
        conversation = get_object_or_404(Conversation, conversation_id=conversation_id)
        
        # Vérifier que l'utilisateur est participant
        if not conversation.participants.filter(user_id=self.request.user.user_id).exists():
            raise PermissionDenied("Vous n'êtes pas participant à cette conversation")
        
        serializer.save(
            sender=self.request.user,
            conversation=conversation
        )
        
        # Mettre à jour le timestamp de la conversation
        conversation.save()  # Ceci met à jour le champ updated_at

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marquer un message comme lu"""
        message = self.get_object()
        message.is_read = True
        message.save()
        return Response(
            {'message': 'Message marqué comme lu'}, 
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Marquer tous les messages d'une conversation comme lus"""
        conversation_id = self.kwargs.get('conversation_pk')
        if not conversation_id:
            return Response(
                {'error': 'ID de conversation requis'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        messages = self.get_queryset().filter(is_read=False)
        messages.update(is_read=True)
        
        return Response(
            {'message': f'{messages.count()} messages marqués comme lus'}, 
            status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self.check_object_permissions(request, instance):
            return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self.check_object_permissions(request, instance):
            return Response({'detail': 'You do not have permission to perform this action.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)