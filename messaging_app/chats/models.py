import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    # Primary key UUID
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Required fields from the schema
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Will be hashed by Django
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Additional fields for the User model
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    last_seen = models.DateTimeField(default=timezone.now)
    
    # Use email as username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

class Conversation(models.Model):
    conversation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']

class Message(models.Model):
    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message_body = models.TextField()  # Renamed from 'content'
    sent_at = models.DateTimeField(auto_now_add=True)  # Renamed from 'created_at'
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['sent_at']