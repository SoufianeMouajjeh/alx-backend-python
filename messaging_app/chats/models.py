# chats/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    """
    Extended User model with additional fields for messaging app
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email


class Conversation(models.Model):
    """
    Model to track conversations between users
    """
    CONVERSATION_TYPES = [
        ('private', 'Private'),
        ('group', 'Group'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=100, blank=True, null=True)
    conversation_type = models.CharField(
        max_length=20, 
        choices=CONVERSATION_TYPES, 
        default='private'
    )
    participants = models.ManyToManyField(
        User, 
        related_name='conversations',
        through='ConversationParticipant'
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_conversations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'conversations'
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-updated_at']

    def __str__(self):
        if self.title:
            return self.title
        participants = self.participants.all()[:2]
        if len(participants) == 2:
            return f"{participants[0].username} & {participants[1].username}"
        return f"Conversation {str(self.id)[:8]}"

    @property
    def last_message(self):
        return self.messages.last()

    def get_other_participant(self, user):
        """Get the other participant in a private conversation"""
        if self.conversation_type == 'private':
            return self.participants.exclude(id=user.id).first()
        return None


class ConversationParticipant(models.Model):
    """
    Through model to track additional participant information
    """
    PARTICIPANT_ROLES = [
        ('member', 'Member'),
        ('admin', 'Admin'),
        ('owner', 'Owner'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
        related_name='participant_details'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='conversation_participations'
    )
    role = models.CharField(max_length=20, choices=PARTICIPANT_ROLES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notifications_enabled = models.BooleanField(default=True)
    last_read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'conversation_participants'
        unique_together = ['conversation', 'user']
        verbose_name = 'Conversation Participant'
        verbose_name_plural = 'Conversation Participants'

    def __str__(self):
        return f"{self.user.username} in {self.conversation}"


class Message(models.Model):
    """
    Model for individual messages in conversations
    """
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    content = models.TextField(blank=True, null=True)
    file_url = models.URLField(blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)  # in bytes
    
    # Message status
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Reply functionality
    reply_to = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='replies'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['created_at']

    def __str__(self):
        content_preview = self.content[:50] if self.content else f"[{self.message_type}]"
        return f"{self.sender.username}: {content_preview}"

    def save(self, *args, **kwargs):
        # Update conversation's updated_at when a message is created/updated
        if self.pk is None:  # New message
            super().save(*args, **kwargs)
            self.conversation.updated_at = timezone.now()
            self.conversation.save(update_fields=['updated_at'])
        else:
            super().save(*args, **kwargs)


class MessageReadStatus(models.Model):
    """
    Track which users have read which messages
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE, 
        related_name='read_statuses'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='message_read_statuses'
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message_read_status'
        unique_together = ['message', 'user']
        verbose_name = 'Message Read Status'
        verbose_name_plural = 'Message Read Statuses'

    def __str__(self):
        return f"{self.user.username} read message {str(self.message.id)[:8]}"