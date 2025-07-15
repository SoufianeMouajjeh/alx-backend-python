import django_filters
from .models import Message

class MessageFilter(django_filters.FilterSet):
    sent_after = django_filters.DateTimeFilter(field_name='sent_at', lookup_expr='gte')
    sent_before = django_filters.DateTimeFilter(field_name='sent_at', lookup_expr='lte')
    sender = django_filters.CharFilter(field_name='sender__username', lookup_expr='iexact')
    conversation = django_filters.CharFilter(field_name='conversation__conversation_id', lookup_expr='exact')

    class Meta:
        model = Message
        fields = ['sender', 'conversation', 'sent_after', 'sent_before']