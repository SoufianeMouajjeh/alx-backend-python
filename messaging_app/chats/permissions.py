from rest_framework import permissions

class IsParticipantOfConversation(permissions.BasePermission):
    """
    Allows only participants to send, view, update, and delete messages in a conversation.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # For Conversation objects
        if hasattr(obj, 'participants'):
            return request.user in obj.participants.all()
        # For Message objects
        if hasattr(obj, 'conversation'):
            is_participant = request.user in obj.conversation.participants.all()
            if request.method in ['PUT', 'PATCH', 'DELETE']:
                return is_participant
            return is_participant
        return False