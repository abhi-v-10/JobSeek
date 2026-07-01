"""
Application Management System — Filters

Django-filter FilterSets for structured query parameter filtering on
application list endpoints. Supports the full range of filter options
required by the API spec.

Usage:
    GET /api/applications/?status=applied&company=Google
    GET /api/applications/?date_from=2024-01-01&source=linkedin
"""

from __future__ import annotations

import django_filters

from .models import JobApplication


class ApplicationFilter(django_filters.FilterSet):
    """
    FilterSet for JobApplication list endpoints.

    Supported filters:
        status       — Exact match on application status
        source       — Exact match on application source
        archived     — Boolean filter for archived flag
        withdrawn    — Boolean filter for withdrawn flag
        job          — Exact match on job ID
        company      — Case-insensitive contains on job company name
        position     — Case-insensitive contains on job position/title
        date_from    — Applications applied on or after this datetime
        date_to      — Applications applied on or before this datetime
        created_from — Applications created on or after this datetime
        created_to   — Applications created on or before this datetime
    """

    company = django_filters.CharFilter(
        field_name="job__company",
        lookup_expr="icontains",
        help_text="Filter by company name (case-insensitive contains).",
    )
    position = django_filters.CharFilter(
        field_name="job__position",
        lookup_expr="icontains",
        help_text="Filter by job position/title (case-insensitive contains).",
    )
    date_from = django_filters.DateTimeFilter(
        field_name="applied_at",
        lookup_expr="gte",
        help_text="Filter applications applied on or after this date.",
    )
    date_to = django_filters.DateTimeFilter(
        field_name="applied_at",
        lookup_expr="lte",
        help_text="Filter applications applied on or before this date.",
    )
    created_from = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
        help_text="Filter applications created on or after this date.",
    )
    created_to = django_filters.DateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        help_text="Filter applications created on or before this date.",
    )

    class Meta:
        model = JobApplication
        fields = [
            "status",
            "source",
            "archived",
            "withdrawn",
            "job",
        ]
