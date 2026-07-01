"""
Application Management System — Views

DRF ViewSets and API endpoints for job applications and nested resources.
Uses the service layer (ApplicationService, AnalyticsService) to keep
controllers thin.

Endpoints:
    - JobApplicationViewSet: CRUD + custom actions (dashboard, upcoming, follow-ups, analytics)
    - ApplicationTimelineViewSet: Scoped list/create for timeline events
    - ApplicationNoteViewSet: Scoped CRUD for notes
    - InterviewRoundViewSet: Scoped CRUD for interview rounds
    - OfferViewSet: Scoped CRUD for offers (singleton-like per application)
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import JobApplication, ApplicationTimeline, ApplicationNote, InterviewRound, Offer
from .serializers import (
    JobApplicationListSerializer,
    JobApplicationDetailSerializer,
    JobApplicationCreateSerializer,
    JobApplicationUpdateSerializer,
    ApplicationTimelineSerializer,
    ApplicationNoteSerializer,
    InterviewRoundSerializer,
    OfferSerializer,
)
from .permissions import IsApplicationOwner
from .pagination import ApplicationPagination
from .filters import ApplicationFilter
from .services.application_service import ApplicationService
from .services.analytics_service import AnalyticsService


class JobApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing job applications.
    Supports list, retrieve, create, update, and soft delete (archiving).
    """
    permission_classes = [permissions.IsAuthenticated, IsApplicationOwner]
    pagination_class = ApplicationPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ApplicationFilter
    search_fields = ["job__company", "job__position", "notes", "recruiter_name", "recruiter_email"]
    ordering_fields = ["created_at", "updated_at", "applied_at", "status"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        """
        Return applications belonging to the user.
        Admins can view all.
        """
        if self.request.user.is_staff:
            return JobApplication.objects.select_related("job").all()
        return JobApplication.objects.filter(user=self.request.user, archived=False).select_related("job")

    def get_serializer_class(self):
        if self.action in ["list", "follow_ups"]:
            return JobApplicationListSerializer
        elif self.action == "retrieve":
            return JobApplicationDetailSerializer
        elif self.action == "create":
            return JobApplicationCreateSerializer
        elif self.action == "upcoming_interviews":
            return InterviewRoundSerializer
        return JobApplicationUpdateSerializer

    def perform_create(self, serializer):
        # We delegate application creation to the service layer
        # so we get resume snapshotting and initial timeline logic.
        validated_data = serializer.validated_data
        application = ApplicationService.create_application(
            user=self.request.user,
            job=validated_data["job"],
            cover_letter=validated_data.get("cover_letter", ""),
            notes=validated_data.get("notes", ""),
            recruiter_name=validated_data.get("recruiter_name", ""),
            recruiter_email=validated_data.get("recruiter_email", ""),
            expected_salary=validated_data.get("expected_salary"),
            source=validated_data.get("source", ""),
            status=validated_data.get("status", "draft"),
        )
        # Bind the created instance back to the serializer representation
        serializer.instance = application

    def perform_update(self, serializer):
        new_status = serializer.validated_data.get("status")
        if new_status:
            instance = self.get_object()
            if new_status != instance.status:
                from django.utils import timezone
                from .constants import ApplicationStatus
                if new_status == ApplicationStatus.APPLIED and not instance.applied_at:
                    serializer.validated_data["applied_at"] = timezone.now()
                if new_status == ApplicationStatus.WITHDRAWN:
                    serializer.validated_data["withdrawn"] = True
        serializer.save()

    def perform_destroy(self, instance):
        # Soft delete: mark as archived
        instance.archived = True
        instance.save(update_fields=["archived", "updated_at"])

    # ── Custom Endpoints ──────────────────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        """GET /api/applications/dashboard/"""
        stats = AnalyticsService.get_dashboard_stats(request.user)
        return Response(stats, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="upcoming-interviews")
    def upcoming_interviews(self, request):
        """GET /api/applications/upcoming-interviews/"""
        rounds = ApplicationService.get_upcoming_interviews(request.user)
        serializer = InterviewRoundSerializer(rounds, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="follow-ups")
    def follow_ups(self, request):
        """GET /api/applications/follow-ups/"""
        apps = ApplicationService.get_follow_ups(request.user)
        serializer = JobApplicationListSerializer(apps, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="analytics")
    def analytics(self, request):
        """GET /api/applications/analytics/"""
        data = AnalyticsService.get_analytics(request.user)
        return Response(data, status=status.HTTP_200_OK)


class BaseNestedViewSet(viewsets.ModelViewSet):
    """
    Abstract viewset for resources nested under an application.
    Enforces application ownership and scoping.
    """
    permission_classes = [permissions.IsAuthenticated, IsApplicationOwner]

    def get_application(self):
        app_id = self.kwargs.get("application_id")
        if self.request.user.is_staff:
            return get_object_or_404(JobApplication, id=app_id)
        return get_object_or_404(JobApplication, id=app_id, user=self.request.user)


class ApplicationTimelineViewSet(BaseNestedViewSet):
    """
    Timeline events nested under a specific application.
    GET /api/applications/{application_id}/timeline/
    POST /api/applications/{application_id}/timeline/
    """
    serializer_class = ApplicationTimelineSerializer

    def get_queryset(self):
        app = self.get_application()
        return ApplicationTimeline.objects.filter(application=app).order_by("-timestamp")

    def perform_create(self, serializer):
        app = self.get_application()
        serializer.save(application=app, created_by=self.request.user)


class ApplicationNoteViewSet(BaseNestedViewSet):
    """
    Private notes nested under a specific application.
    GET /api/applications/{application_id}/notes/
    POST /api/applications/{application_id}/notes/
    PATCH /api/applications/{application_id}/notes/{id}/
    DELETE /api/applications/{application_id}/notes/{id}/
    """
    serializer_class = ApplicationNoteSerializer

    def get_queryset(self):
        app = self.get_application()
        return ApplicationNote.objects.filter(application=app).order_by("-created_at")

    def perform_create(self, serializer):
        app = self.get_application()
        serializer.save(application=app, author=self.request.user)


class InterviewRoundViewSet(BaseNestedViewSet):
    """
    Interview rounds nested under a specific application.
    GET /api/applications/{application_id}/interviews/
    POST /api/applications/{application_id}/interviews/
    PATCH /api/applications/{application_id}/interviews/{id}/
    DELETE /api/applications/{application_id}/interviews/{id}/
    """
    serializer_class = InterviewRoundSerializer

    def get_queryset(self):
        app = self.get_application()
        return InterviewRound.objects.filter(application=app).order_by("round_number")

    def perform_create(self, serializer):
        app = self.get_application()
        serializer.save(application=app)


class OfferViewSet(BaseNestedViewSet):
    """
    Offers nested under a specific application.
    GET /api/applications/{application_id}/offer/
    POST /api/applications/{application_id}/offer/
    PATCH /api/applications/{application_id}/offer/{id}/
    DELETE /api/applications/{application_id}/offer/{id}/
    """
    serializer_class = OfferSerializer

    def get_queryset(self):
        app = self.get_application()
        return Offer.objects.filter(application=app)

    def perform_create(self, serializer):
        app = self.get_application()
        # Enforce single Offer per application
        if Offer.objects.filter(application=app).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {"detail": "An offer record already exists for this application. Use PUT/PATCH to update it."}
            )
        serializer.save(application=app)
