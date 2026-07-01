"""
Application Management System — Analytics Service

Aggregation and analytics logic for dashboard and reporting endpoints.
Uses Django ORM aggregation functions for performant, single-query
statistics wherever possible.

Designed to power SeekBot AI features:
    "How many jobs have I applied for?"
    "What is my interview rate?"
    "What is my offer rate?"
    "Which companies rejected me?"
    "How has my application success changed over time?"
    "What companies am I waiting on?"
    "Which roles give me the best success?"
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Avg, Count, ExpressionWrapper, F, fields
from django.db.models.functions import TruncMonth
from django.utils import timezone

from ..constants import (
    ApplicationStatus,
    INTERVIEW_STATUSES,
    OFFER_STATUSES,
)
from ..models import JobApplication


class AnalyticsService:
    """Service class for computing application analytics and dashboard statistics."""

    @classmethod
    def get_dashboard_stats(cls, user: Any) -> dict[str, Any]:
        """
        Compute summary statistics for the user's application dashboard.

        Uses a single aggregation query to count applications per status,
        then derives all rates from those counts. This is O(1) queries
        regardless of the number of applications.

        Returns:
            {
                "total_applications": int,
                "by_status": {"draft": 5, "applied": 12, ...},
                "active_count": int,
                "interviewing_count": int,
                "offers_count": int,
                "rejected_count": int,
                "withdrawn_count": int,
                "offer_rate": float,      # percentage
                "interview_rate": float,  # percentage
                "success_rate": float,    # percentage
            }
        """
        base_qs = JobApplication.objects.filter(user=user, archived=False)

        # Single-query aggregation: group by status → count
        status_rows = (
            base_qs.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        status_counts: dict[str, int] = dict(status_rows)

        total = sum(status_counts.values())

        # Derive group counts from the per-status breakdown
        interviewing = sum(
            status_counts.get(s, 0) for s in INTERVIEW_STATUSES
        )
        offers = sum(status_counts.get(s, 0) for s in OFFER_STATUSES)
        rejected = status_counts.get(ApplicationStatus.REJECTED, 0)
        withdrawn = status_counts.get(ApplicationStatus.WITHDRAWN, 0)
        accepted = status_counts.get(ApplicationStatus.OFFER_ACCEPTED, 0)

        # Active = everything except terminal states
        terminal_count = (
            accepted
            + status_counts.get(ApplicationStatus.OFFER_DECLINED, 0)
            + rejected
            + withdrawn
        )
        active = total - terminal_count

        # Rate calculations (guard against division by zero)
        offer_rate = round((offers / total) * 100, 1) if total > 0 else 0.0
        interview_rate = round((interviewing / total) * 100, 1) if total > 0 else 0.0
        success_rate = round((accepted / total) * 100, 1) if total > 0 else 0.0

        return {
            "total_applications": total,
            "by_status": status_counts,
            "active_count": active,
            "interviewing_count": interviewing,
            "offers_count": offers,
            "rejected_count": rejected,
            "withdrawn_count": withdrawn,
            "offer_rate": offer_rate,
            "interview_rate": interview_rate,
            "success_rate": success_rate,
        }

    @classmethod
    def get_analytics(cls, user: Any) -> dict[str, Any]:
        """
        Compute detailed analytics for the user's application history.

        Includes trend data, conversion rates, response times, and
        source breakdown — all the data SeekBot needs for career
        progress analysis and recommendations.

        Returns:
            {
                "application_trend": [{"month": "2024-01-01T00:00:00", "count": 5}, ...],
                "response_rate": float,
                "interview_conversion": float,
                "offer_conversion": float,
                "average_response_days": float | None,
                "top_sources": {"linkedin": 10, "referral": 5, ...},
                "status_distribution": {"applied": 15, "rejected": 3, ...},
            }
        """
        base_qs = JobApplication.objects.filter(user=user, archived=False)

        # ── Application trend (last 12 months) ──────────────────────────
        twelve_months_ago = timezone.now() - timedelta(days=365)
        monthly_trend = list(
            base_qs.filter(created_at__gte=twelve_months_ago)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
            .values("month", "count")
        )
        # Serialize datetime objects to ISO strings
        for entry in monthly_trend:
            if entry["month"]:
                entry["month"] = entry["month"].isoformat()

        # ── Conversion rate calculations ─────────────────────────────────
        total = base_qs.count()

        # Only count applications that were actually submitted
        applied_qs = base_qs.exclude(
            status__in=[
                ApplicationStatus.DRAFT,
                ApplicationStatus.READY_TO_APPLY,
            ]
        )
        total_applied = applied_qs.count()

        # Response rate: % that moved beyond "applied" (got some response)
        responded = applied_qs.exclude(
            status=ApplicationStatus.APPLIED
        ).count()
        response_rate = (
            round((responded / total_applied) * 100, 1)
            if total_applied > 0
            else 0.0
        )

        # Interview conversion: % of submitted apps reaching interview
        # Count apps that reached or passed interview stages
        interview_or_beyond_statuses = list(INTERVIEW_STATUSES) + list(OFFER_STATUSES)
        interviewed = base_qs.filter(
            status__in=interview_or_beyond_statuses
        ).count()
        interview_conversion = (
            round((interviewed / total_applied) * 100, 1)
            if total_applied > 0
            else 0.0
        )

        # Offer conversion: % of interviews that resulted in offers
        offered = base_qs.filter(status__in=list(OFFER_STATUSES)).count()
        offer_conversion = (
            round((offered / interviewed) * 100, 1)
            if interviewed > 0
            else 0.0
        )

        # ── Average response time ────────────────────────────────────────
        # Approximate: difference between applied_at and updated_at for
        # applications that received a response
        avg_response = (
            applied_qs.filter(applied_at__isnull=False)
            .exclude(status=ApplicationStatus.APPLIED)
            .aggregate(
                avg_days=Avg(
                    ExpressionWrapper(
                        F("updated_at") - F("applied_at"),
                        output_field=fields.DurationField(),
                    )
                )
            )
        )
        avg_response_days: float | None = None
        if avg_response["avg_days"]:
            avg_response_days = round(
                avg_response["avg_days"].total_seconds() / 86400, 1
            )

        # ── Source breakdown ─────────────────────────────────────────────
        source_rows = (
            base_qs.values("source")
            .annotate(count=Count("id"))
            .order_by("-count")
            .values_list("source", "count")
        )
        top_sources: dict[str, int] = dict(source_rows)

        # ── Status distribution ──────────────────────────────────────────
        status_rows = (
            base_qs.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        status_distribution: dict[str, int] = dict(status_rows)

        return {
            "application_trend": monthly_trend,
            "response_rate": response_rate,
            "interview_conversion": interview_conversion,
            "offer_conversion": offer_conversion,
            "average_response_days": avg_response_days,
            "top_sources": top_sources,
            "status_distribution": status_distribution,
        }
