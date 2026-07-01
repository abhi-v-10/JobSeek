"""
Application Management System — Serializers

DRF serializers for all normalized models in the applications app.
Supports nesting for detail views, lightweight serialization for lists,
and write serializers with validation.

Serializers:
    - ApplicationTimelineSerializer
    - ApplicationNoteSerializer
    - InterviewRoundSerializer
    - OfferSerializer
    - JobApplicationListSerializer
    - JobApplicationDetailSerializer
    - JobApplicationCreateSerializer
    - JobApplicationUpdateSerializer
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.jobs.serializers import JobSerializer
from .models import JobApplication, ApplicationTimeline, ApplicationNote, InterviewRound, Offer
from .constants import ApplicationStatus, InterviewType, InterviewStatus, ApplicationSource

User = get_user_model()


class ApplicationTimelineSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = ApplicationTimeline
        fields = [
            "id",
            "application",
            "event_type",
            "event_type_display",
            "description",
            "timestamp",
            "created_by",
            "created_by_username",
        ]
        read_only_fields = ["id", "application", "timestamp", "created_by", "created_by_username"]


class ApplicationNoteSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = ApplicationNote
        fields = [
            "id",
            "application",
            "author",
            "author_username",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "application", "author", "author_username", "created_at", "updated_at"]


class InterviewRoundSerializer(serializers.ModelSerializer):
    interview_type_display = serializers.CharField(source="get_interview_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = InterviewRound
        fields = [
            "id",
            "application",
            "round_number",
            "interview_type",
            "interview_type_display",
            "scheduled_time",
            "interviewer",
            "location",
            "status",
            "status_display",
            "feedback",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "application", "interview_type_display", "status_display", "created_at", "updated_at"]


class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = [
            "id",
            "application",
            "company_package",
            "base_salary",
            "bonus",
            "stock",
            "joining_bonus",
            "location",
            "remote",
            "joining_date",
            "deadline",
            "accepted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "application", "created_at", "updated_at"]


class JobApplicationListSerializer(serializers.ModelSerializer):
    company = serializers.CharField(source="job.company", read_only=True)
    position = serializers.CharField(source="job.position", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job",
            "company",
            "position",
            "status",
            "status_display",
            "applied_at",
            "updated_at",
            "recruiter_name",
            "recruiter_email",
            "interview_date",
            "source",
            "source_display",
            "archived",
            "withdrawn",
        ]
        read_only_fields = ["id", "applied_at", "updated_at", "status_display", "source_display"]


class JobApplicationDetailSerializer(serializers.ModelSerializer):
    job = JobSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    timeline_events = ApplicationTimelineSerializer(many=True, read_only=True)
    application_notes = ApplicationNoteSerializer(many=True, read_only=True)
    interview_rounds = InterviewRoundSerializer(many=True, read_only=True)
    offer = OfferSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "user",
            "job",
            "resume_snapshot",
            "cover_letter",
            "status",
            "status_display",
            "applied_at",
            "updated_at",
            "created_at",
            "notes",
            "recruiter_name",
            "recruiter_email",
            "interview_date",
            "offer_salary",
            "expected_salary",
            "source",
            "source_display",
            "archived",
            "withdrawn",
            "timeline_events",
            "application_notes",
            "interview_rounds",
            "offer",
        ]
        read_only_fields = [
            "id",
            "user",
            "applied_at",
            "created_at",
            "updated_at",
            "status_display",
            "source_display",
        ]


class JobApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job",
            "cover_letter",
            "notes",
            "recruiter_name",
            "recruiter_email",
            "expected_salary",
            "source",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        user = self.context["request"].user
        job = attrs.get("job")
        if job and JobApplication.objects.filter(user=user, job=job).exists():
            raise serializers.ValidationError("An application for this job already exists.")
        return attrs


class JobApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = [
            "cover_letter",
            "notes",
            "recruiter_name",
            "recruiter_email",
            "expected_salary",
            "source",
            "status",
            "interview_date",
            "offer_salary",
            "archived",
            "applied_at",
            "withdrawn",
        ]
        read_only_fields = ["applied_at", "withdrawn"]

    def validate(self, attrs):
        new_status = attrs.get("status")
        if new_status and self.instance:
            from .validators import validate_status_transition
            validate_status_transition(self.instance.status, new_status)
        return attrs
