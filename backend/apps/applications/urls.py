"""
Application Management System — URLs

Declares explicit URL endpoints for job applications and all nested sub-resources.
Using explicit mappings ensures clear API contracts and avoids dependency issues
with third-party nested routers.
"""

from django.urls import path
from .views import (
    JobApplicationViewSet,
    ApplicationTimelineViewSet,
    ApplicationNoteViewSet,
    InterviewRoundViewSet,
    OfferViewSet,
)

app_name = "applications"

urlpatterns = [
    # Custom dashboard, analytical & reminder endpoints
    path("dashboard/", JobApplicationViewSet.as_view({"get": "dashboard"}), name="application-dashboard"),
    path("upcoming-interviews/", JobApplicationViewSet.as_view({"get": "upcoming_interviews"}), name="application-upcoming-interviews"),
    path("follow-ups/", JobApplicationViewSet.as_view({"get": "follow_ups"}), name="application-follow-ups"),
    path("analytics/", JobApplicationViewSet.as_view({"get": "analytics"}), name="application-analytics"),

    # Main JobApplication CRUD
    path("", JobApplicationViewSet.as_view({"get": "list", "post": "create"}), name="application-list-create"),
    path("<int:pk>/", JobApplicationViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="application-detail"),

    # Scoped Nested Timeline Events
    path("<int:application_id>/timeline/", ApplicationTimelineViewSet.as_view({"get": "list", "post": "create"}), name="timeline-list-create"),

    # Scoped Nested Application Notes
    path("<int:application_id>/notes/", ApplicationNoteViewSet.as_view({"get": "list", "post": "create"}), name="notes-list-create"),
    path("<int:application_id>/notes/<int:pk>/", ApplicationNoteViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="notes-detail"),

    # Scoped Nested Interview Rounds
    path("<int:application_id>/interviews/", InterviewRoundViewSet.as_view({"get": "list", "post": "create"}), name="interviews-list-create"),
    path("<int:application_id>/interviews/<int:pk>/", InterviewRoundViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="interviews-detail"),

    # Scoped Nested Offers (One-to-One / Singleton-like CRUD)
    path("<int:application_id>/offer/", OfferViewSet.as_view({"get": "list", "post": "create"}), name="offer-list-create"),
    path("<int:application_id>/offer/<int:pk>/", OfferViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="offer-detail"),
]
