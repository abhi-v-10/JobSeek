"""
Application Management System — Signals

Django signals that automatically create timeline events when key
application lifecycle events occur. This ensures the timeline is
always synchronized without requiring explicit calls from every code path.

Signal flow:
    1. pre_save on JobApplication → stash previous status for change detection
    2. post_save on JobApplication → log creation or status change events
    3. post_save on InterviewRound → log "Interview Scheduled" event
    4. post_save on Offer → log "Offer Received" event

Design Note:
    Signals are best-effort for timeline logging. They never raise
    exceptions that would roll back the parent transaction.
"""

from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .constants import ApplicationStatus, TimelineEventType
from .models import ApplicationTimeline, InterviewRound, JobApplication, Offer

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# JobApplication Signals
# ══════════════════════════════════════════════════════════════════════════════


@receiver(pre_save, sender=JobApplication)
def track_previous_status(sender: type, instance: JobApplication, **kwargs) -> None:
    """
    Stash the previous status on the instance before save, so
    post_save can detect status changes and create timeline events.
    """
    if instance.pk:
        try:
            previous = JobApplication.objects.only("status").get(pk=instance.pk)
            instance._previous_status = previous.status  # type: ignore[attr-defined]
        except JobApplication.DoesNotExist:
            instance._previous_status = None  # type: ignore[attr-defined]
    else:
        instance._previous_status = None  # type: ignore[attr-defined]


@receiver(post_save, sender=JobApplication)
def create_application_timeline_event(
    sender: type,
    instance: JobApplication,
    created: bool,
    **kwargs,
) -> None:
    """
    Auto-create timeline events for application creation and status changes.

    On creation:
        Creates a "Application Created" event.

    On status change:
        Creates a typed event (e.g., "Rejected", "Offer Received") or
        a generic "Status Changed" event if no specific type matches.
    """
    try:
        if created:
            ApplicationTimeline.objects.create(
                application=instance,
                event_type=TimelineEventType.CREATED,
                description="Application created.",
                created_by=instance.user,
            )
            return

        # Detect status change
        previous_status: str | None = getattr(instance, "_previous_status", None)
        if previous_status and previous_status != instance.status:
            old_label = dict(ApplicationStatus.choices).get(
                previous_status, previous_status
            )
            new_label = instance.get_status_display()

            # Map specific statuses to their dedicated event types
            event_type_map: dict[str, str] = {
                ApplicationStatus.REJECTED: TimelineEventType.REJECTED,
                ApplicationStatus.WITHDRAWN: TimelineEventType.WITHDRAWN,
                ApplicationStatus.OFFER_RECEIVED: TimelineEventType.OFFER_RECEIVED,
                ApplicationStatus.OFFER_ACCEPTED: TimelineEventType.OFFER_ACCEPTED,
                ApplicationStatus.OFFER_DECLINED: TimelineEventType.OFFER_DECLINED,
                ApplicationStatus.RECRUITER_CONTACTED: TimelineEventType.RECRUITER_CONTACTED,
            }
            event_type = event_type_map.get(
                instance.status, TimelineEventType.STATUS_CHANGED
            )

            ApplicationTimeline.objects.create(
                application=instance,
                event_type=event_type,
                description=f"Status changed from '{old_label}' to '{new_label}'.",
                created_by=instance.user,
            )
    except Exception:
        # Timeline creation is best-effort — never block the save
        logger.exception("Failed to create timeline event for application %s", instance.pk)


# ══════════════════════════════════════════════════════════════════════════════
# InterviewRound Signals
# ══════════════════════════════════════════════════════════════════════════════


@receiver(post_save, sender=InterviewRound)
def create_interview_timeline_event(
    sender: type,
    instance: InterviewRound,
    created: bool,
    **kwargs,
) -> None:
    """Auto-create a timeline event when a new interview round is scheduled."""
    if not created:
        return

    try:
        interview_label = instance.get_interview_type_display()
        scheduled = instance.scheduled_time
        time_str = scheduled.strftime("%b %d, %Y at %I:%M %p") if scheduled else "TBD"

        ApplicationTimeline.objects.create(
            application=instance.application,
            event_type=TimelineEventType.INTERVIEW_SCHEDULED,
            description=(
                f"Interview round {instance.round_number} ({interview_label}) "
                f"scheduled for {time_str}."
            ),
            created_by=instance.application.user,
        )
    except Exception:
        logger.exception(
            "Failed to create timeline event for interview round %s",
            instance.pk,
        )


# ══════════════════════════════════════════════════════════════════════════════
# Offer Signals
# ══════════════════════════════════════════════════════════════════════════════


@receiver(post_save, sender=Offer)
def create_offer_timeline_event(
    sender: type,
    instance: Offer,
    created: bool,
    **kwargs,
) -> None:
    """Auto-create a timeline event when an offer is received."""
    if not created:
        return

    try:
        salary_str = (
            f"${instance.base_salary:,.2f}" if instance.base_salary else "details pending"
        )

        ApplicationTimeline.objects.create(
            application=instance.application,
            event_type=TimelineEventType.OFFER_RECEIVED,
            description=f"Offer received — base salary: {salary_str}.",
            created_by=instance.application.user,
        )
    except Exception:
        logger.exception(
            "Failed to create timeline event for offer %s", instance.pk
        )
