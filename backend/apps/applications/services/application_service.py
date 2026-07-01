"""
Application Management System — Application Service

Business logic layer for application management operations.
Keeps ViewSets thin by encapsulating all complex logic here.

Responsibilities:
    - Application creation with immutable resume snapshot
    - Status transitions with state machine validation
    - Follow-up identification (stale applications)
    - Upcoming interview queries

All methods are classmethods for clean calling semantics and
easy mocking in tests.
"""

from __future__ import annotations

import logging
import os
from datetime import timedelta
from typing import Any

from django.core.files import File
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ..constants import ApplicationStatus, FOLLOW_UP_THRESHOLD_DAYS
from ..models import InterviewRound, JobApplication
from ..validators import validate_status_transition, validate_unique_application

logger = logging.getLogger(__name__)


class ApplicationService:
    """Service class encapsulating application management business logic."""

    @classmethod
    @transaction.atomic
    def create_application(
        cls,
        user: Any,
        job: Any,
        *,
        cover_letter: str = "",
        notes: str = "",
        recruiter_name: str = "",
        recruiter_email: str = "",
        expected_salary: Any = None,
        source: str = "",
        status: str = ApplicationStatus.DRAFT,
    ) -> JobApplication:
        """
        Create a new job application with an immutable resume snapshot.

        Validates uniqueness, creates the application record, and copies
        the user's current resume to create an immutable snapshot that
        won't change even if the user updates their resume later.

        Args:
            user: The authenticated user creating the application.
            job: The Job instance being applied to.
            cover_letter: Optional cover letter text.
            notes: Optional quick notes.
            recruiter_name: Optional recruiter name.
            recruiter_email: Optional recruiter email.
            expected_salary: Optional expected salary (Decimal).
            source: Application source (from ApplicationSource choices).
            status: Initial status (defaults to 'draft').

        Returns:
            The created JobApplication instance.

        Raises:
            ValidationError: If a duplicate application exists.
        """
        # Validate uniqueness before creating
        validate_unique_application(user_id=user.id, job_id=job.id)

        # Build creation kwargs
        application_data: dict[str, Any] = {
            "user": user,
            "job": job,
            "cover_letter": cover_letter or None,
            "notes": notes,
            "recruiter_name": recruiter_name,
            "recruiter_email": recruiter_email,
            "expected_salary": expected_salary,
            "status": status,
        }

        # Only set source if provided, otherwise model default applies
        if source:
            application_data["source"] = source

        # Set applied_at timestamp if starting directly in "applied" status
        if status == ApplicationStatus.APPLIED:
            application_data["applied_at"] = timezone.now()

        application = JobApplication.objects.create(**application_data)

        # Best-effort: snapshot the user's current resume
        cls._snapshot_resume(application, user)

        return application

    @classmethod
    def _snapshot_resume(cls, application: JobApplication, user: Any) -> None:
        """
        Copy the user's current resume file to create an immutable snapshot.

        The snapshot is stored separately so that updating the user's
        profile resume does not alter historical application records.
        This is a best-effort operation — failures are logged but
        do not block application creation.
        """
        try:
            profile = getattr(user, "profile", None)
            if profile and profile.resume and profile.resume.name:
                source_file = profile.resume
                original_name = os.path.basename(source_file.name)
                ext = os.path.splitext(original_name)[1] or ".pdf"
                snapshot_name = f"app_{application.pk}_resume{ext}"

                source_file.open("rb")
                try:
                    application.resume_snapshot.save(
                        snapshot_name,
                        File(source_file),
                        save=True,
                    )
                finally:
                    source_file.close()
        except Exception:
            logger.exception(
                "Failed to snapshot resume for application %s", application.pk
            )

    @classmethod
    @transaction.atomic
    def update_status(
        cls,
        application: JobApplication,
        new_status: str,
        user: Any,
    ) -> JobApplication:
        """
        Update an application's status with state machine validation.

        Validates the transition against the state machine, applies the
        status change, and handles side effects (setting applied_at,
        marking withdrawn). The post_save signal automatically creates
        the timeline event.

        Args:
            application: The application to update.
            new_status: The target status value.
            user: The user performing the update.

        Returns:
            The updated JobApplication instance.

        Raises:
            ValidationError: If the status transition is invalid.
        """
        # Validate the transition is allowed
        validate_status_transition(application.status, new_status)

        # Apply the change
        application.status = new_status
        update_fields = ["status", "updated_at"]

        # Side effect: set applied_at on first transition to "applied"
        if new_status == ApplicationStatus.APPLIED and not application.applied_at:
            application.applied_at = timezone.now()
            update_fields.append("applied_at")

        # Side effect: mark as withdrawn
        if new_status == ApplicationStatus.WITHDRAWN:
            application.withdrawn = True
            update_fields.append("withdrawn")

        application.save(update_fields=update_fields)
        return application

    @classmethod
    def get_follow_ups(cls, user: Any) -> QuerySet[JobApplication]:
        """
        Get applications that need follow-up attention.

        Returns applications in an active, non-draft state that haven't
        had any update for more than FOLLOW_UP_THRESHOLD_DAYS.

        SeekBot query: "Which applications need follow-up?"
        """
        threshold = timezone.now() - timedelta(days=FOLLOW_UP_THRESHOLD_DAYS)

        return (
            JobApplication.objects.filter(
                user=user,
                archived=False,
                status__in=[
                    ApplicationStatus.APPLIED,
                    ApplicationStatus.UNDER_REVIEW,
                    ApplicationStatus.RECRUITER_CONTACTED,
                ],
                updated_at__lte=threshold,
            )
            .select_related("job")
            .order_by("updated_at")
        )

    @classmethod
    def get_upcoming_interviews(cls, user: Any) -> QuerySet[InterviewRound]:
        """
        Get upcoming interview rounds ordered by scheduled time.

        Returns only interviews that are in the future and have
        status "scheduled" (excludes completed/cancelled).

        SeekBot query: "What interviews do I have coming up?"
        """
        now = timezone.now()

        return (
            InterviewRound.objects.filter(
                application__user=user,
                application__archived=False,
                scheduled_time__gte=now,
                status="scheduled",
            )
            .select_related("application", "application__job")
            .order_by("scheduled_time")
        )
