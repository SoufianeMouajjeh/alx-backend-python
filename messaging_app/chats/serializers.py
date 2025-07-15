from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import User, Conversation, Message, ConversationParticipant, MessageReadStatus


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model
    """
    full_name = serializers.SerializerMethodField()
    unread_messages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'phone_number', 'avatar', 'bio', 
            'is_online', 'last_seen', 'created_at', 'unread_messages_count'
        ]
        read_only_fields = ['id', 'created_at', 'last_seen']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_unread_messages_count(self, obj):
        # This would need to be optimized in production
        return Message.objects.filter(
            conversation__participants=obj,
            created_at__gt=obj.conversation_participations.values('last_read_at')
        ).count()


class UserSimpleSerializer(serializers.ModelSerializer):
    """
    Simple serializer for User model (for nested relationships)
    """
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'avatar', 'is_online', 'last_seen']
        read_only_fields = ['id']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class MessageReadStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for MessageReadStatus model
    """
    user = UserSimpleSerializer(read_only=True)
    
    class Meta:
        model = MessageReadStatus
        fields = ['id', 'user', 'read_at']
        read_only_fields = ['id', 'read_at']


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model
    """
    sender = UserSimpleSerializer(read_only=True)
    reply_to = serializers.SerializerMethodField()
    read_statuses = MessageReadStatusSerializer(many=True, read_only=True)
    is_read_by_user = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'message_type', 'content', 
            'file_url', 'file_name', 'file_size', 'is_edited', 'edited_at',
            'is_deleted', 'deleted_at', 'reply_to', 'read_statuses', 
            'is_read_by_user', 'replies_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sender', 'is_edited', 'edited_at', 'is_deleted', 
            'deleted_at', 'created_at', 'updated_at'
        ]

    def get_reply_to(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'sender': UserSimpleSerializer(obj.reply_to.sender).data,
                'content': obj.reply_to.content,
                'message_type': obj.reply_to.message_type,
                'created_at': obj.reply_to.created_at
            }
        return None

    def get_is_read_by_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.read_statuses.filter(user=request.user).exists()
        return False

    def get_replies_count(self, obj):
        return obj.replies.count()

    def create(self, validated_data):
        # Set the sender to the current user
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Mark as edited if content is being updated
        if 'content' in validated_data and validated_data['content'] != instance.content:
            validated_data['is_edited'] = True
            validated_data['edited_at'] = timezone.now()
        return super().update(instance, validated_data)


class MessageCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating messages
    """
    class Meta:
        model = Message
        fields = ['conversation', 'message_type', 'content', 'file_url', 'file_name', 'file_size', 'reply_to']

    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """
    Serializer for ConversationParticipant model
    """
    user = UserSimpleSerializer(read_only=True)
    unread_messages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'id', 'user', 'role', 'joined_at', 'left_at', 'is_active',
            'notifications_enabled', 'last_read_at', 'unread_messages_count'
        ]
        read_only_fields = ['id', 'joined_at', 'left_at']

    def get_unread_messages_count(self, obj):
        return obj.conversation.messages.filter(
            created_at__gt=obj.last_read_at
        ).exclude(sender=obj.user).count()


class ConversationSerializer(serializers.ModelSerializer):
    """
    Serializer for Conversation model with nested relationships
    """
    participants = UserSimpleSerializer(many=True, read_only=True)
    created_by = UserSimpleSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    participant_details = ConversationParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_messages_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'conversation_type', 'participants', 'created_by',
            'created_at', 'updated_at', 'is_active', 'messages', 
            'participant_details', 'last_message', 'unread_messages_count',
            'other_participant'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return MessageSerializer(last_message, context=self.context).data
        return None

    def get_unread_messages_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participant = obj.participant_details.filter(user=request.user).first()
            if participant:
                return obj.messages.filter(
                    created_at__gt=participant.last_read_at
                ).exclude(sender=request.user).count()
        return 0

    def get_other_participant(self, obj):
        """Get the other participant in a private conversation"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.conversation_type == 'private':
            other_participant = obj.get_other_participant(request.user)
            if other_participant:
                return UserSimpleSerializer(other_participant).data
        return None

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing conversations (without nested messages)
    """
    participants = UserSimpleSerializer(many=True, read_only=True)
    created_by = UserSimpleSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_messages_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'conversation_type', 'participants', 'created_by',
            'created_at', 'updated_at', 'is_active', 'last_message', 
            'unread_messages_count', 'other_participant'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return {
                'id': last_message.id,
                'sender': UserSimpleSerializer(last_message.sender).data,
                'content': last_message.content,
                'message_type': last_message.message_type,
                'created_at': last_message.created_at
            }
        return None

    def get_unread_messages_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            participant = obj.participant_details.filter(user=request.user).first()
            if participant:
                return obj.messages.filter(
                    created_at__gt=participant.last_read_at
                ).exclude(sender=request.user).count()
        return 0

    def get_other_participant(self, obj):
        """Get the other participant in a private conversation"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and obj.conversation_type == 'private':
            other_participant = obj.get_other_participant(request.user)
            if other_participant:
                return UserSimpleSerializer(other_participant).data
        return None


class ConversationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating conversations
    """
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=True
    )
    
    class Meta:
        model = Conversation
        fields = ['title', 'conversation_type', 'participant_ids']

    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids')
        validated_data['created_by'] = self.context['request'].user
        
        conversation = super().create(validated_data)
        
        # Add creator as a participant
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=self.context['request'].user,
            role='owner'
        )
        
        # Add other participants
        for participant_id in participant_ids:
            try:
                user = User.objects.get(id=participant_id)
                if user != self.context['request'].user:  # Don't add creator twice
                    ConversationParticipant.objects.create(
                        conversation=conversation,
                        user=user,
                        role='member'
                    )
            except User.DoesNotExist:
                pass
        
        return conversation


class MessageMarkAsReadSerializer(serializers.Serializer):
    """
    Serializer for marking messages as read
    """
    message_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True
    )

    def create(self, validated_data):
        message_ids = validated_data['message_ids']
        user = self.context['request'].user
        
        for message_id in message_ids:
            try:
                message = Message.objects.get(id=message_id)
                MessageReadStatus.objects.get_or_create(
                    message=message,
                    user=user
                )
            except Message.DoesNotExist:
                pass
        
        return {'message_ids': message_ids}