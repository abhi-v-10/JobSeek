from django.contrib import admin
from .models import Job, JobApplication, ViewedJob, SavedJob, JobInteractionStats

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "position", "company", "location", "job_type", "type", "status", "posted_by", "created_at")
    list_filter = ("status", "job_type", "type", "created_at")
    search_fields = ("position", "company", "location", "posted_by__username", "posted_by__email")
    readonly_fields = ("created_at", "updated_at")

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "user", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("job__position", "job__company", "user__username", "user__email")
    readonly_fields = ("created_at",)

@admin.register(ViewedJob)
class ViewedJobAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "user", "viewed_at")
    list_filter = ("viewed_at",)
    search_fields = ("job__position", "job__company", "user__username", "user__email")
    readonly_fields = ("viewed_at",)

@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("job__position", "job__company", "user__username", "user__email")
    readonly_fields = ("created_at",)

@admin.register(JobInteractionStats)
class JobInteractionStatsAdmin(admin.ModelAdmin):
    list_display = ("job", "applied_count", "viewed_count", "saved_count", "updated_at")
    search_fields = ("job__position", "job__company")
    readonly_fields = ("updated_at",)
