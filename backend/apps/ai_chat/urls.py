from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatSessionViewSet

app_name = "chat"

# Using a router for standard RESTful endpoints
router = DefaultRouter()
router.register(r"sessions", ChatSessionViewSet, basename="chat-session")

urlpatterns = [
    # Include router URLs (provides /sessions/ and /sessions/{id}/ and /sessions/{id}/messages/)
    path("", include(router.urls)),

    # Legacy Compatibility Layer - Ensuring we do NOT break existing session APIs
    # These match the previous non-standard URL structures
    path(
        "sessions/create/",
        ChatSessionViewSet.as_view({"post": "create"}),
        name="chat-session-create-legacy"
    ),
    path(
        "sessions/<str:id>/delete/",
        ChatSessionViewSet.as_view({"delete": "destroy"}),
        name="chat-session-delete-legacy"
    ),
]
