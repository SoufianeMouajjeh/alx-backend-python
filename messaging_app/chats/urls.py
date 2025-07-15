from django.urls import path, include
from rest_framework import routers
from rest_framework_nested import routers as nested_routers
from .views import ConversationViewSet, MessageViewSet

# Création du router principal
router = routers.DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')

# Création du router imbriqué pour les messages dans les conversations
conversations_router = nested_routers.NestedDefaultRouter(
    router, 
    r'conversations', 
    lookup='conversation'
)
conversations_router.register(
    r'messages', 
    MessageViewSet, 
    basename='conversation-messages'
)

urlpatterns = [
    # Inclure toutes les routes du router principal
    path('', include(router.urls)),
    
    # Inclure toutes les routes du router imbriqué
    path('', include(conversations_router.urls)),
]

# Les routes générées seront :
# GET/POST /api/conversations/ - Liste/Création des conversations
# GET/PUT/PATCH/DELETE /api/conversations/{id}/ - Détails d'une conversation
# POST /api/conversations/{id}/add_participant/ - Ajouter un participant
# POST /api/conversations/{id}/leave_conversation/ - Quitter une conversation
# GET/POST /api/conversations/{conversation_id}/messages/ - Messages d'une conversation
# GET/PUT/PATCH/DELETE /api/conversations/{conversation_id}/messages/{id}/ - Détails d'un message
# POST /api/conversations/{conversation_id}/messages/{id}/mark_as_read/ - Marquer comme lu
# POST /api/conversations/{conversation_id}/messages/mark_all_as_read/ - Marquer tous comme lus