from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from apps.messaging.models import Conversation
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.users.models import Profile

from apps.applications.models import JobApplication
from apps.applications.services.application_service import ApplicationService
from apps.applications.constants import ApplicationStatus
from .email_utils import send_application_email
from .models import Job, JobInteractionStats, SavedJob, ViewedJob
from .serializers import (
    ApplicantSerializer,
    JobApplicationSerializer,
    JobSerializer,
    SavedJobSerializer,
    ViewedJobSerializer,
)

# ── Helpers ────────────────────────────────────────────────────────────────────


def _serialize_counts(stats):
    return {
        "applied_count": stats.applied_count,
        "viewed_count": stats.viewed_count,
        "saved_count": stats.saved_count,
    }


def _change_interaction_count(job, field_name, delta=1):
    with transaction.atomic():
        stats, _ = JobInteractionStats.objects.select_for_update().get_or_create(
            job=job
        )
        current_value = getattr(stats, field_name)
        new_value = max(0, current_value + delta)
        setattr(stats, field_name, new_value)
        stats.save(update_fields=[field_name, "updated_at"])
    return stats


def _get_or_create_stats(job):
    stats, _ = JobInteractionStats.objects.get_or_create(job=job)
    return stats


# ── Job List / Create ──────────────────────────────────────────────────────────


class JobListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = JobSerializer

    def get_queryset(self):
        return (
            Job.objects.filter(status="open")  # Only show open jobs publicly
            .select_related("posted_by")
            .prefetch_related("interaction_stats")
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        if profile.user_type != "poster":
            raise PermissionDenied("Only users with poster role can create jobs.")
        serializer.save(posted_by=self.request.user)


# ── Job Detail ─────────────────────────────────────────────────────────────────


class JobDetailAPIView(generics.RetrieveAPIView):
    queryset = Job.objects.select_related("posted_by").prefetch_related(
        "interaction_stats"
    )
    serializer_class = JobSerializer
    lookup_field = "id"
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


# ── Job Update (Poster only) ───────────────────────────────────────────────────


class JobUpdateAPIView(generics.UpdateAPIView):
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"
    http_method_names = ["patch"]

    def get_queryset(self):
        return Job.objects.filter(posted_by=self.request.user)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def get_object(self):
        obj = get_object_or_404(Job, id=self.kwargs["id"])
        if obj.posted_by_id != self.request.user.id:
            raise PermissionDenied("You can only edit your own jobs.")
        return obj


# ── My Jobs (Poster's own posted jobs) ────────────────────────────────────────


class MyJobsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        jobs = (
            Job.objects.filter(posted_by=request.user)
            .select_related("posted_by")
            .prefetch_related("interaction_stats", "application_records__user__profile")
            .order_by("-created_at")
        )
        ctx = {"request": request}
        result = []
        for job in jobs:
            job_data = JobSerializer(job, context=ctx).data
            applicants = JobApplication.objects.filter(job=job).select_related("user__profile").all()
            job_data["applicants"] = ApplicantSerializer(applicants, many=True).data
            result.append(job_data)
        return Response(result, status=status.HTTP_200_OK)


# ── Job Applicants (per job, poster only) ─────────────────────────────────────


class JobApplicantsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id):
        job = get_object_or_404(Job, id=id)
        if job.posted_by_id != request.user.id:
            raise PermissionDenied("Only the job poster can view applicants.")
        applicants = JobApplication.objects.filter(job=job).select_related(
            "user__profile"
        )
        return Response(
            ApplicantSerializer(applicants, many=True).data, status=status.HTTP_200_OK
        )


# ── Apply Eligibility ─────────────────────────────────────────────────────────


class ApplyEligibilityAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, id):
        job = get_object_or_404(Job, id=id)
        profile = request.user.profile

        missing_fields = []
        if job.job_type == "corporate":
            if not profile.resume:
                missing_fields.append("resume")
            if not profile.linkedin_url:
                missing_fields.append("linkedin_url")
            if not profile.github_url:
                missing_fields.append("github_url")

        return Response(
            {
                "eligible": len(missing_fields) == 0,
                "missing_fields": missing_fields,
                "job_type": job.job_type,
            }
        )


# ── Apply ──────────────────────────────────────────────────────────────────────


class ApplyJobAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        job = get_object_or_404(Job, id=id)
        profile = request.user.profile

        # Block poster from applying to their own job
        if job.posted_by_id == request.user.id:
            return Response(
                {"detail": "You cannot apply for your own job posting."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Eligibility check for corporate
        if job.job_type == "corporate":
            missing = []
            if not profile.resume:
                missing.append("resume")
            if not profile.linkedin_url:
                missing.append("linkedin_url")
            if not profile.github_url:
                missing.append("github_url")
            if missing:
                return Response(
                    {
                        "detail": "Please complete your profile (resume, LinkedIn, GitHub) before applying to corporate jobs.",
                        "missing_fields": missing,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Consent check
        if not request.data.get("consent"):
            return Response(
                {
                    "detail": "You must agree to share your profile information to apply."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if JobApplication.objects.filter(user=request.user, job=job).exists():
            stats = _get_or_create_stats(job)
            return Response(
                {
                    "detail": "You have already applied to this job.",
                    "counts": _serialize_counts(stats),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            application = ApplicationService.create_application(
                user=request.user,
                job=job,
                status=ApplicationStatus.APPLIED,
            )
            stats = _change_interaction_count(job, "applied_count", delta=1)

            # Create/Get conversation
            participant_1 = job.posted_by
            participant_2 = request.user
            # Ensure consistent order for unique constraint if we weren't using job_id too,
            # but here it's per job so we use applicant as p2.
            conversation, created = Conversation.objects.get_or_create(
                participant_1=participant_1, participant_2=participant_2, job=job
            )

            # Send Email
            optional_message = request.data.get("message", "")
            send_application_email(job, request.user, conversation.id, optional_message)

        serializer = JobApplicationSerializer(application, context={"request": request})
        return Response(
            {
                "application": serializer.data,
                "counts": _serialize_counts(stats),
                "conversation_id": conversation.id,
            },
            status=status.HTTP_201_CREATED,
        )


# ── View ───────────────────────────────────────────────────────────────────────


class MarkViewedJobAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        job = get_object_or_404(Job, id=id)
        viewed_job, created = ViewedJob.objects.get_or_create(
            user=request.user, job=job
        )
        if created:
            stats = _change_interaction_count(job, "viewed_count", delta=1)
        else:
            stats = _get_or_create_stats(job)
        serializer = ViewedJobSerializer(viewed_job, context={"request": request})
        return Response(
            {"viewed_job": serializer.data, "counts": _serialize_counts(stats)},
            status=status.HTTP_200_OK,
        )


# ── Save / Unsave ──────────────────────────────────────────────────────────────


class SaveJobAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        job = get_object_or_404(Job, id=id)
        if SavedJob.objects.filter(user=request.user, job=job).exists():
            stats = _get_or_create_stats(job)
            return Response(
                {"detail": "Job is already saved.", "counts": _serialize_counts(stats)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        saved_job = SavedJob.objects.create(user=request.user, job=job)
        stats = _change_interaction_count(job, "saved_count", delta=1)
        serializer = SavedJobSerializer(saved_job, context={"request": request})
        return Response(
            {"saved_job": serializer.data, "counts": _serialize_counts(stats)},
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, id):
        job = get_object_or_404(Job, id=id)
        deleted_count, _ = SavedJob.objects.filter(user=request.user, job=job).delete()
        if deleted_count == 0:
            stats = _get_or_create_stats(job)
            return Response(
                {"detail": "Saved job not found.", "counts": _serialize_counts(stats)},
                status=status.HTTP_404_NOT_FOUND,
            )
        stats = _change_interaction_count(job, "saved_count", delta=-1)
        return Response(
            {"detail": "Job unsaved successfully.", "counts": _serialize_counts(stats)},
            status=status.HTTP_200_OK,
        )


# ── Dashboard ──────────────────────────────────────────────────────────────────


class JobDashboardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ctx = {"request": request}
        recently_applied_qs = (
            JobApplication.objects.filter(user=request.user)
            .select_related("job", "job__posted_by")
            .prefetch_related("job__interaction_stats")
            .order_by("-created_at")[:5]
        )
        recently_viewed_qs = (
            ViewedJob.objects.filter(user=request.user)
            .select_related("job", "job__posted_by")
            .prefetch_related("job__interaction_stats")
            .order_by("-viewed_at")[:5]
        )
        starred_jobs_qs = (
            SavedJob.objects.filter(user=request.user)
            .select_related("job", "job__posted_by")
            .prefetch_related("job__interaction_stats")
            .order_by("-created_at")
        )

        data = {
            "recently_applied": JobApplicationSerializer(
                recently_applied_qs, many=True, context=ctx
            ).data,
            "recently_viewed": ViewedJobSerializer(
                recently_viewed_qs, many=True, context=ctx
            ).data,
            "starred_jobs": SavedJobSerializer(
                starred_jobs_qs, many=True, context=ctx
            ).data,
            "applied_jobs_count": JobApplication.objects.filter(
                user=request.user
            ).count(),
            "saved_jobs_count": SavedJob.objects.filter(user=request.user).count(),
        }
        return Response(data, status=status.HTTP_200_OK)


# ── Job Search API ─────────────────────────────────────────────────────────────

from .serializers import JobSearchSerializer
from .services.job_search_service import search_jobs


class JobSearchAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        filters = {
            "role": request.query_params.get("role"),
            "skills": request.query_params.get("skills"),
            "location": request.query_params.get("location"),
            "remote": request.query_params.get("remote"),
            "job_type": request.query_params.get("job_type"),
            "salary_min": request.query_params.get("salary_min"),
            "salary_max": request.query_params.get("salary_max"),
        }

        # Filter out None values
        filters = {k: v for k, v in filters.items() if v is not None}

        queryset = search_jobs(filters)

        # We can optimize the queryset since we only need certain fields
        queryset = queryset.only(
            "id",
            "position",
            "work",
            "company",
            "location",
            "work_mode",
            "job_type",
            "required_experience_fields",
            "created_at",
        )

        serializer = JobSearchSerializer(queryset, many=True)

        return Response(
            {
                "success": True,
                "count": len(serializer.data),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
