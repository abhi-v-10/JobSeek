from rest_framework import serializers

from .models import Job, SavedJob, ViewedJob
from apps.applications.models import JobApplication


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


class ApplicantSkillSerializer(serializers.Serializer):
    name = serializers.CharField()
    category = serializers.CharField()


class ApplicantDetailSerializer(serializers.ModelSerializer):
    """
    Full applicant profile for a single application — shown only to the
    job poster. Prefers the immutable resume snapshot taken at the time
    of application, falling back to the applicant's current profile resume.
    """
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField()
    mobile_number = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    resume = serializers.SerializerMethodField()
    linkedin_url = serializers.SerializerMethodField()
    github_url = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    message = serializers.CharField(source="cover_letter", read_only=True)
    applied_at = serializers.DateTimeField(source="created_at", read_only=True)
    conversation_id = serializers.SerializerMethodField()

    def _profile(self, obj):
        return getattr(obj.user, "profile", None)

    def _request(self):
        return self.context.get("request")

    def _absolute(self, file_field):
        if not file_field:
            return None
        request = self._request()
        try:
            url = file_field.url
        except ValueError:
            return None
        return request.build_absolute_uri(url) if request else url

    def get_full_name(self, obj):
        profile = self._profile(obj)
        return profile.full_name if profile else ""

    def get_mobile_number(self, obj):
        profile = self._profile(obj)
        return profile.mobile_number if profile else ""

    def get_profile_picture(self, obj):
        profile = self._profile(obj)
        return self._absolute(profile.profile_picture) if profile else None

    def get_resume(self, obj):
        # Prefer the immutable snapshot taken at application time.
        if obj.resume_snapshot:
            return self._absolute(obj.resume_snapshot)
        profile = self._profile(obj)
        return self._absolute(profile.resume) if profile else None

    def get_linkedin_url(self, obj):
        profile = self._profile(obj)
        return profile.linkedin_url if profile else ""

    def get_github_url(self, obj):
        profile = self._profile(obj)
        return profile.github_url if profile else ""

    def get_skills(self, obj):
        profile = self._profile(obj)
        if not profile:
            return []
        return ApplicantSkillSerializer(profile.skills.all(), many=True).data

    def get_conversation_id(self, obj):
        from apps.messaging.models import Conversation

        conversation = Conversation.objects.filter(
            participant_1=obj.job.posted_by, participant_2=obj.user, job=obj.job
        ).first()
        return conversation.id if conversation else None

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "mobile_number",
            "profile_picture",
            "resume",
            "linkedin_url",
            "github_url",
            "skills",
            "message",
            "status",
            "applied_at",
            "conversation_id",
        ]
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


class JobSearchSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    company_name = serializers.CharField(source="company")
    is_remote = serializers.SerializerMethodField()
    skills = serializers.CharField(source="required_experience_fields")

    def get_title(self, obj):
        return obj.position or obj.work

    def get_is_remote(self, obj):
        return obj.work_mode == "remote"

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "company_name",
            "location",
            "is_remote",
            "job_type",
            "skills",
            "created_at"
        ]
