"""
Application Management System — Models

Normalized data models representing the complete lifecycle of a job application.
Designed as the single source of truth for all application tracking data,
and optimized for SeekBot AI analytics and recommendations.

Models:
    JobApplication  — Core application record with status tracking
    ApplicationTimeline — Chronological event log per application
    ApplicationNote — Private notes attached to applications
    InterviewRound — Individual interview rounds with scheduling & feedback
    Offer — Compensation and offer details (one-to-one with application)

Design Principles:
    - Each model has a single responsibility
    - Foreign keys use CASCADE for cleanup on deletion
    - Indexes optimized for common query patterns (user-scoped, status-filtered)
    - Timestamps on every model for audit trails
    - Soft-delete via `archived` flag on JobApplication
"""

from django.conf import settings
from django.db import models

from .constants import (
    ApplicationSource,
    ApplicationStatus,
    InterviewStatus,
    InterviewType,
    INTERVIEW_STATUSES,
    OFFER_STATUSES,
    TERMINAL_STATUSES,
    TimelineEventType,
)


class JobApplication(models.Model):
    """
    Represents a single job application submitted by a user.

    This is the central model — all other application-related models
    reference it via ForeignKey. It tracks the full lifecycle from
    draft to final outcome using a strict state machine.

    The status field transitions are validated by validators.validate_status_transition()
    and enforced in the service layer.

    Attributes:
        user: The applicant who owns this application.
        job: The job listing this application targets.
        resume_snapshot: Immutable copy of the resume at application time.
        cover_letter: Cover letter text (nullable, for future module integration).
        status: Current lifecycle stage (see ApplicationStatus).
        applied_at: Set automatically when status transitions to 'applied'.
    """

    # ── Core relationships ───────────────────────────────────────────────
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tracked_applications",
        help_text="The user who submitted this application.",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="application_records",
        help_text="The job listing this application is for.",
    )

    # ── Documents ────────────────────────────────────────────────────────
    resume_snapshot = models.FileField(
        upload_to="application_resumes/",
        null=True,
        blank=True,
        help_text="Immutable copy of the resume used at the time of application.",
    )
    cover_letter = models.TextField(
        null=True,
        blank=True,
        help_text="Cover letter content submitted with this application.",
    )

    # ── Status tracking ──────────────────────────────────────────────────
    status = models.CharField(
        max_length=30,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.DRAFT,
        db_index=True,
        help_text="Current status in the application lifecycle.",
    )
    applied_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when status moved to 'applied'.",
    )

    # ── Metadata ─────────────────────────────────────────────────────────
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Quick notes about this application.",
    )
    recruiter_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Name of the recruiter or hiring contact.",
    )
    recruiter_email = models.EmailField(
        blank=True,
        default="",
        help_text="Email of the recruiter or hiring contact.",
    )
    interview_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Next upcoming interview date.",
    )

    # ── Compensation ─────────────────────────────────────────────────────
    offer_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Offered salary amount.",
    )
    expected_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Expected/desired salary amount.",
    )

    # ── Source & flags ───────────────────────────────────────────────────
    source = models.CharField(
        max_length=30,
        choices=ApplicationSource.choices,
        default=ApplicationSource.OTHER,
        help_text="How the user discovered this job opening.",
    )
    archived = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft-delete flag. Archived applications are hidden from default views.",
    )
    withdrawn = models.BooleanField(
        default=False,
        help_text="Whether the user has withdrawn this application.",
    )

    # ── Timestamps ───────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "applications_job_application"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "job"],
                name="unique_application_per_user_job",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"], name="idx_app_user_status"),
            models.Index(fields=["user", "archived"], name="idx_app_user_archived"),
            models.Index(fields=["user", "created_at"], name="idx_app_user_created"),
            models.Index(fields=["user", "applied_at"], name="idx_app_user_applied"),
            models.Index(fields=["status", "updated_at"], name="idx_app_status_updated"),
        ]
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"

    def __str__(self) -> str:
        job_title = getattr(self.job, "position", "") or getattr(self.job, "work", "")
        company = getattr(self.job, "company", "")
        return f"{self.user} → {job_title} at {company} [{self.get_status_display()}]"

    @property
    def is_active(self) -> bool:
        """Whether this application is still in an active (non-terminal) state."""
        return self.status not in TERMINAL_STATUSES

    @property
    def is_interviewing(self) -> bool:
        """Whether this application is currently in an interview stage."""
        return self.status in INTERVIEW_STATUSES

    @property
    def has_offer(self) -> bool:
        """Whether this application has received an offer."""
        return self.status in OFFER_STATUSES


class ApplicationTimeline(models.Model):
    """
    Chronological event log for an application.

    Each entry represents a significant event in the application lifecycle.
    Most events are auto-created by signals (see signals.py), but users
    can also manually create custom events via the API.

    SeekBot uses this data for:
        - Reconstructing application history
        - Analyzing response times
        - Identifying patterns in recruiter behavior
    """

    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="timeline_events",
        help_text="The parent application this event belongs to.",
    )
    event_type = models.CharField(
        max_length=30,
        choices=TimelineEventType.choices,
        help_text="Categorized type of this timeline event.",
    )
    description = models.TextField(
        help_text="Human-readable description of the event.",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When this event occurred.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="The user who created this event (null if system-generated).",
    )

    class Meta:
        db_table = "applications_timeline"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(
                fields=["application", "timestamp"],
                name="idx_timeline_app_ts",
            ),
            models.Index(
                fields=["application", "event_type"],
                name="idx_timeline_app_type",
            ),
        ]
        verbose_name = "Timeline Event"
        verbose_name_plural = "Timeline Events"

    def __str__(self) -> str:
        return f"[{self.get_event_type_display()}] {self.description[:60]}"


class ApplicationNote(models.Model):
    """
    Private notes attached to an application by the user.

    These are separate from the quick `notes` field on JobApplication
    to support a full history of detailed notes with timestamps.

    SeekBot uses notes data to understand application context
    and provide personalized recommendations.
    """

    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="application_notes",
        help_text="The parent application this note belongs to.",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
        help_text="The user who wrote this note.",
    )
    note = models.TextField(
        help_text="The note content.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "applications_note"
        ordering = ["-created_at"]
        verbose_name = "Application Note"
        verbose_name_plural = "Application Notes"

    def __str__(self) -> str:
        preview = self.note[:50] + "..." if len(self.note) > 50 else self.note
        return f"Note on App #{self.application_id}: {preview}"


class InterviewRound(models.Model):
    """
    Represents a single interview round within an application.

    An application can have multiple rounds (phone screen, technical,
    behavioral, onsite, etc.). Each round tracks its own schedule,
    interviewer, and feedback.

    SeekBot uses interview data for:
        - Interview preparation based on past rounds
        - Identifying common interview patterns per company
        - Tracking interview success rates by type
    """

    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="interview_rounds",
        help_text="The parent application this round belongs to.",
    )
    round_number = models.PositiveIntegerField(
        help_text="Sequential round number (1, 2, 3, ...).",
    )
    interview_type = models.CharField(
        max_length=30,
        choices=InterviewType.choices,
        help_text="Type of interview for this round.",
    )
    scheduled_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled date and time for this interview.",
    )
    interviewer = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Name of the interviewer.",
    )
    location = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Interview location (physical address or video call URL).",
    )
    status = models.CharField(
        max_length=20,
        choices=InterviewStatus.choices,
        default=InterviewStatus.SCHEDULED,
        help_text="Current status of this interview round.",
    )
    feedback = models.TextField(
        blank=True,
        default="",
        help_text="Post-interview feedback or notes.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "applications_interview_round"
        ordering = ["round_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "round_number"],
                name="unique_interview_round_per_application",
            ),
        ]
        indexes = [
            models.Index(
                fields=["application", "scheduled_time"],
                name="idx_interview_app_time",
            ),
            models.Index(
                fields=["scheduled_time", "status"],
                name="idx_interview_time_status",
            ),
        ]
        verbose_name = "Interview Round"
        verbose_name_plural = "Interview Rounds"

    def __str__(self) -> str:
        return (
            f"Round {self.round_number} ({self.get_interview_type_display()}) "
            f"for App #{self.application_id}"
        )


class Offer(models.Model):
    """
    Compensation and offer details for an application.

    One-to-one with JobApplication — each application can have at most
    one offer record. Stores detailed compensation breakdown for
    comparison and analysis.

    SeekBot uses offer data for:
        - Salary benchmarking and comparison
        - Offer negotiation insights
        - Career progress tracking
        - Total compensation analysis
    """

    application = models.OneToOneField(
        JobApplication,
        on_delete=models.CASCADE,
        related_name="offer",
        help_text="The application this offer is for.",
    )
    company_package = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total compensation package (CTC).",
    )
    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Base salary amount.",
    )
    bonus = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual bonus amount.",
    )
    stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Stock/equity compensation value.",
    )
    joining_bonus = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="One-time joining/signing bonus.",
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Office location for this offer.",
    )
    remote = models.BooleanField(
        default=False,
        help_text="Whether this is a remote position.",
    )
    joining_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected start/joining date.",
    )
    deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Deadline to accept or decline the offer.",
    )
    accepted = models.BooleanField(
        null=True,
        blank=True,
        help_text="None = pending, True = accepted, False = declined.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "applications_offer"
        verbose_name = "Offer"
        verbose_name_plural = "Offers"

    def __str__(self) -> str:
        salary_str = f"${self.base_salary:,.2f}" if self.base_salary else "N/A"
        return f"Offer for App #{self.application_id} — Base: {salary_str}"
