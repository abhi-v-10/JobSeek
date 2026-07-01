"""
Application Management System — Django Admin

Production-quality admin dashboard configuration for application tracking.
Includes inline panels for timeline events, notes, interview rounds, and offers
to allow managing complete applications from a single detail view.
"""

from django.contrib import admin
from .models import JobApplication, ApplicationTimeline, ApplicationNote, InterviewRound, Offer


class ApplicationTimelineInline(admin.TabularInline):
    model = ApplicationTimeline
    extra = 0
    ordering = ["-timestamp"]
    readonly_fields = ["timestamp", "created_by"]


class ApplicationNoteInline(admin.StackedInline):
    model = ApplicationNote
    extra = 0
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]


class InterviewRoundInline(admin.TabularInline):
    model = InterviewRound
    extra = 0
    ordering = ["round_number"]
    readonly_fields = ["created_at", "updated_at"]


class OfferInline(admin.StackedInline):
    model = Offer
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "job",
        "status",
        "applied_at",
        "archived",
        "withdrawn",
        "created_at",
    )
    list_filter = (
        "status",
        "source",
        "archived",
        "withdrawn",
        "created_at",
        "applied_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "job__company",
        "job__position",
        "notes",
        "recruiter_name",
        "recruiter_email",
    )
    readonly_fields = ("created_at", "updated_at", "applied_at")
    fieldsets = (
        ("Core Information", {
            "fields": ("user", "job", "status", "applied_at")
        }),
        ("Documents", {
            "fields": ("resume_snapshot", "cover_letter")
        }),
        ("Recruitment Contact", {
            "fields": ("recruiter_name", "recruiter_email", "source")
        }),
        ("Details & Salary", {
            "fields": ("notes", "interview_date", "offer_salary", "expected_salary")
        }),
        ("System Flags", {
            "fields": ("archived", "withdrawn", "created_at", "updated_at")
        }),
    )
    inlines = [
        ApplicationTimelineInline,
        ApplicationNoteInline,
        InterviewRoundInline,
        OfferInline,
    ]


@admin.register(ApplicationTimeline)
class ApplicationTimelineAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "event_type", "timestamp", "created_by")
    list_filter = ("event_type", "timestamp")
    search_fields = ("application__job__company", "application__job__position", "description")


@admin.register(ApplicationNote)
class ApplicationNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "author", "created_at")
    search_fields = ("application__job__company", "application__job__position", "note")


@admin.register(InterviewRound)
class InterviewRoundAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "round_number", "interview_type", "scheduled_time", "status")
    list_filter = ("interview_type", "status", "scheduled_time")
    search_fields = ("application__job__company", "application__job__position", "interviewer")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "base_salary", "location", "remote", "accepted")
    list_filter = ("remote", "accepted", "joining_date")
    search_fields = ("application__job__company", "application__job__position", "location")
