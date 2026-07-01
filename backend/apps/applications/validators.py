"""
Application Management System — Validators

Business rule validators for status transitions and duplicate application
prevention. Used by both the serializer layer (for API validation) and the
service layer (for programmatic enforcement).

These validators raise rest_framework.exceptions.ValidationError so they
integrate cleanly with DRF's exception handling pipeline.
"""

from __future__ import annotations

from rest_framework.exceptions import ValidationError

from .constants import ApplicationStatus, VALID_STATUS_TRANSITIONS


def validate_status_transition(current_status: str, new_status: str) -> None:
    """
    Validate that a status transition is permitted by the state machine.

    The state machine is defined in constants.VALID_STATUS_TRANSITIONS.
    Terminal states (offer_accepted, offer_declined, rejected, withdrawn)
    have no outgoing transitions.

    Args:
        current_status: The current status of the application.
        new_status: The proposed new status.

    Raises:
        ValidationError: If the transition is not allowed.
    """
    # No-op: setting the same status is always allowed
    if current_status == new_status:
        return

    allowed = VALID_STATUS_TRANSITIONS.get(current_status, frozenset())

    if new_status not in allowed:
        # Build human-readable labels for the error message
        status_labels = dict(ApplicationStatus.choices)
        current_label = status_labels.get(current_status, current_status)
        new_label = status_labels.get(new_status, new_status)
        allowed_labels = sorted(
            status_labels.get(s, s) for s in allowed
        )

        raise ValidationError(
            {
                "status": (
                    f"Invalid status transition from '{current_label}' to '{new_label}'. "
                    f"Allowed transitions: {', '.join(allowed_labels) if allowed_labels else 'none (terminal state)'}."
                )
            }
        )


def validate_unique_application(
    user_id: int,
    job_id: int,
    instance_id: int | None = None,
) -> None:
    """
    Validate that no duplicate application exists for the same user + job.

    The uniqueness constraint is also enforced at the database level via
    UniqueConstraint on JobApplication, but this validator provides a
    user-friendly error message before hitting the DB.

    Args:
        user_id: The applicant's user ID.
        job_id: The target job's ID.
        instance_id: Exclude this application ID (for updates).

    Raises:
        ValidationError: If a duplicate application already exists.
    """
    from .models import JobApplication

    queryset = JobApplication.objects.filter(
        user_id=user_id,
        job_id=job_id,
    )

    if instance_id is not None:
        queryset = queryset.exclude(pk=instance_id)

    if queryset.exists():
        raise ValidationError(
            {
                "job": (
                    "An application for this job already exists. "
                    "You cannot create duplicate applications for the same job."
                )
            }
        )
