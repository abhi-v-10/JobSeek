"""
Application Management System — Constants & Enums

Centralized source of truth for all choices, enums, and business rules.
Every status, event type, interview type, and state machine rule is
defined here for consistency across models, serializers, validators,
services, and admin.

These constants also power SeekBot AI's analytical groupings:
    - ACTIVE_STATUSES  → "How many applications are in progress?"
    - INTERVIEW_STATUSES → "What is my interview rate?"
    - OFFER_STATUSES → "What is my offer rate?"
    - SUCCESS_STATUSES → "What is my success rate?"
"""

from django.db import models


# ── Application Status (lifecycle stages) ────────────────────────────────────


class ApplicationStatus(models.TextChoices):
    """
    Ordered lifecycle stages of a job application.
    Flows from initial → active → terminal states.
    """

    DRAFT = "draft", "Draft"
    READY_TO_APPLY = "ready_to_apply", "Ready to Apply"
    APPLIED = "applied", "Applied"
    UNDER_REVIEW = "under_review", "Under Review"
    RECRUITER_CONTACTED = "recruiter_contacted", "Recruiter Contacted"
    OA_SCHEDULED = "oa_scheduled", "OA Scheduled"
    TECHNICAL_INTERVIEW = "technical_interview", "Technical Interview"
    HR_INTERVIEW = "hr_interview", "HR Interview"
    FINAL_INTERVIEW = "final_interview", "Final Interview"
    OFFER_RECEIVED = "offer_received", "Offer Received"
    OFFER_ACCEPTED = "offer_accepted", "Offer Accepted"
    OFFER_DECLINED = "offer_declined", "Offer Declined"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


# ── Timeline Event Types ─────────────────────────────────────────────────────


class TimelineEventType(models.TextChoices):
    """Types of events that can appear on an application's timeline."""

    CREATED = "created", "Application Created"
    STATUS_CHANGED = "status_changed", "Status Changed"
    NOTE_ADDED = "note_added", "Note Added"
    INTERVIEW_SCHEDULED = "interview_scheduled", "Interview Scheduled"
    INTERVIEW_COMPLETED = "interview_completed", "Interview Completed"
    OFFER_RECEIVED = "offer_received", "Offer Received"
    OFFER_ACCEPTED = "offer_accepted", "Offer Accepted"
    OFFER_DECLINED = "offer_declined", "Offer Declined"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"
    FOLLOW_UP = "follow_up", "Follow Up"
    RECRUITER_CONTACTED = "recruiter_contacted", "Recruiter Contacted"
    CUSTOM = "custom", "Custom Event"


# ── Interview Types ──────────────────────────────────────────────────────────


class InterviewType(models.TextChoices):
    """Types of interview rounds."""

    HR = "hr", "HR"
    TECHNICAL = "technical", "Technical"
    MANAGER = "manager", "Manager"
    SYSTEM_DESIGN = "system_design", "System Design"
    BEHAVIORAL = "behavioral", "Behavioral"
    CODING = "coding", "Coding"
    ONLINE_ASSESSMENT = "online_assessment", "Online Assessment"


# ── Interview Status ─────────────────────────────────────────────────────────


class InterviewStatus(models.TextChoices):
    """Status of an individual interview round."""

    SCHEDULED = "scheduled", "Scheduled"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    RESCHEDULED = "rescheduled", "Rescheduled"
    NO_SHOW = "no_show", "No Show"


# ── Application Source ───────────────────────────────────────────────────────


class ApplicationSource(models.TextChoices):
    """How the user discovered or applied for the job."""

    COMPANY_WEBSITE = "company_website", "Company Website"
    LINKEDIN = "linkedin", "LinkedIn"
    INDEED = "indeed", "Indeed"
    GLASSDOOR = "glassdoor", "Glassdoor"
    REFERRAL = "referral", "Referral"
    CAREER_FAIR = "career_fair", "Career Fair"
    RECRUITER = "recruiter", "Recruiter"
    JOBSEEK = "jobseek", "JobSeek"
    OTHER = "other", "Other"


# ══════════════════════════════════════════════════════════════════════════════
# STATUS TRANSITION STATE MACHINE
# ══════════════════════════════════════════════════════════════════════════════
#
# Each status maps to the frozenset of statuses it can transition to.
# Terminal states (offer_accepted, offer_declined, rejected, withdrawn)
# have empty transition sets — no outgoing edges.
#
# Visual flow:
#
#   draft → ready_to_apply → applied → under_review ─┐
#                                │                     │
#                                ├─→ recruiter_contacted ─┐
#                                │                         │
#                                ▼                         ▼
#                           oa_scheduled ──→ technical_interview
#                                                   │
#                                                   ▼
#                                            hr_interview
#                                                   │
#                                                   ▼
#                                           final_interview
#                                                   │
#                                                   ▼
#                                           offer_received
#                                              │      │
#                                              ▼      ▼
#                                    offer_accepted  offer_declined
#
#   Any active state → withdrawn
#   Most active states → rejected
#

VALID_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    ApplicationStatus.DRAFT: frozenset({
        ApplicationStatus.READY_TO_APPLY,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.READY_TO_APPLY: frozenset({
        ApplicationStatus.APPLIED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.APPLIED: frozenset({
        ApplicationStatus.UNDER_REVIEW,
        ApplicationStatus.RECRUITER_CONTACTED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.UNDER_REVIEW: frozenset({
        ApplicationStatus.RECRUITER_CONTACTED,
        ApplicationStatus.OA_SCHEDULED,
        ApplicationStatus.TECHNICAL_INTERVIEW,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.RECRUITER_CONTACTED: frozenset({
        ApplicationStatus.OA_SCHEDULED,
        ApplicationStatus.TECHNICAL_INTERVIEW,
        ApplicationStatus.HR_INTERVIEW,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.OA_SCHEDULED: frozenset({
        ApplicationStatus.TECHNICAL_INTERVIEW,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.TECHNICAL_INTERVIEW: frozenset({
        ApplicationStatus.HR_INTERVIEW,
        ApplicationStatus.FINAL_INTERVIEW,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.HR_INTERVIEW: frozenset({
        ApplicationStatus.FINAL_INTERVIEW,
        ApplicationStatus.TECHNICAL_INTERVIEW,
        ApplicationStatus.OFFER_RECEIVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.FINAL_INTERVIEW: frozenset({
        ApplicationStatus.OFFER_RECEIVED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    }),
    ApplicationStatus.OFFER_RECEIVED: frozenset({
        ApplicationStatus.OFFER_ACCEPTED,
        ApplicationStatus.OFFER_DECLINED,
    }),
    # Terminal states — no outgoing transitions
    ApplicationStatus.OFFER_ACCEPTED: frozenset(),
    ApplicationStatus.OFFER_DECLINED: frozenset(),
    ApplicationStatus.REJECTED: frozenset(),
    ApplicationStatus.WITHDRAWN: frozenset(),
}


# ══════════════════════════════════════════════════════════════════════════════
# STATUS GROUPINGS FOR ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
# Pre-computed frozensets for efficient membership checks in analytics queries.

ACTIVE_STATUSES: frozenset[str] = frozenset({
    ApplicationStatus.DRAFT,
    ApplicationStatus.READY_TO_APPLY,
    ApplicationStatus.APPLIED,
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.RECRUITER_CONTACTED,
    ApplicationStatus.OA_SCHEDULED,
    ApplicationStatus.TECHNICAL_INTERVIEW,
    ApplicationStatus.HR_INTERVIEW,
    ApplicationStatus.FINAL_INTERVIEW,
    ApplicationStatus.OFFER_RECEIVED,
})

INTERVIEW_STATUSES: frozenset[str] = frozenset({
    ApplicationStatus.OA_SCHEDULED,
    ApplicationStatus.TECHNICAL_INTERVIEW,
    ApplicationStatus.HR_INTERVIEW,
    ApplicationStatus.FINAL_INTERVIEW,
})

TERMINAL_STATUSES: frozenset[str] = frozenset({
    ApplicationStatus.OFFER_ACCEPTED,
    ApplicationStatus.OFFER_DECLINED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
})

OFFER_STATUSES: frozenset[str] = frozenset({
    ApplicationStatus.OFFER_RECEIVED,
    ApplicationStatus.OFFER_ACCEPTED,
    ApplicationStatus.OFFER_DECLINED,
})

SUCCESS_STATUSES: frozenset[str] = frozenset({
    ApplicationStatus.OFFER_RECEIVED,
    ApplicationStatus.OFFER_ACCEPTED,
})

# ── Follow-up configuration ─────────────────────────────────────────────────
# Number of days without activity before an application is flagged for follow-up.
FOLLOW_UP_THRESHOLD_DAYS: int = 7
