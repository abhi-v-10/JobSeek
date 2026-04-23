from rest_framework import serializers

from .models import Job, JobApplication, SavedJob, ViewedJob


class JobSerializer(serializers.ModelSerializer):
    is_saved = serializers.SerializerMethodField()
    is_applied = serializers.SerializerMethodField()
    is_own_job = serializers.SerializerMethodField()
    posted_by_username = serializers.SerializerMethodField()
    applied_count = serializers.SerializerMethodField()
    viewed_count = serializers.SerializerMethodField()
    saved_count = serializers.SerializerMethodField()

    def _request(self):
        return self.context.get("request")

    def get_is_saved(self, obj):
        req = self._request()
        if not req or not req.user.is_authenticated:
            return False
        return SavedJob.objects.filter(user=req.user, job=obj).exists()

    def get_is_applied(self, obj):
        req = self._request()
        if not req or not req.user.is_authenticated:
            return False
        return JobApplication.objects.filter(user=req.user, job=obj).exists()

    def get_is_own_job(self, obj):
        req = self._request()
        if not req or not req.user.is_authenticated:
            return False
        return obj.posted_by_id == req.user.id

    def get_posted_by_username(self, obj):
        try:
            return obj.posted_by.username
        except Exception:
            return None

    def _stats(self, obj):
        stats = getattr(obj, "interaction_stats", None)
        if stats is None:
            from .models import JobInteractionStats
            stats = JobInteractionStats.objects.filter(job=obj).first()
        return stats

    def get_applied_count(self, obj):
        s = self._stats(obj)
        return s.applied_count if s else 0

    def get_viewed_count(self, obj):
        s = self._stats(obj)
        return s.viewed_count if s else 0

    def get_saved_count(self, obj):
        s = self._stats(obj)
        return s.saved_count if s else 0

    class Meta:
        model = Job
        fields = [
            "id",
            "status",
            "posted_by",
            "posted_by_username",
            "job_type",
            "company",
            "position",
            "type",
            "required_experience_years",
            "required_experience_fields",
            "work",
            "daily_work_time",
            "hourly_wage",
            "location",
            "salary_min",
            "salary_max",
            "description",
            "work_mode",
            "is_saved",
            "is_applied",
            "is_own_job",
            "applied_count",
            "viewed_count",
            "saved_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "posted_by"]


class ApplicantSerializer(serializers.ModelSerializer):
    """Lightweight applicant info for poster's My Jobs view."""
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        try:
            return obj.user.profile.full_name
        except Exception:
            return ""

    class Meta:
        model = JobApplication
        fields = ["id", "username", "email", "full_name", "status", "created_at"]
        read_only_fields = fields


class JobApplicationSerializer(serializers.ModelSerializer):
    job = JobSerializer(read_only=True)

    class Meta:
        model = JobApplication
        fields = ["id", "job", "status", "created_at"]
        read_only_fields = fields


class ViewedJobSerializer(serializers.ModelSerializer):
    job = JobSerializer(read_only=True)

    class Meta:
        model = ViewedJob
        fields = ["id", "job", "viewed_at"]
        read_only_fields = fields


class SavedJobSerializer(serializers.ModelSerializer):
    job = JobSerializer(read_only=True)

    class Meta:
        model = SavedJob
        fields = ["id", "job", "created_at"]
        read_only_fields = fields
