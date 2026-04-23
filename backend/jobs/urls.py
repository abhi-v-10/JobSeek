from django.urls import path

from .views import (
    ApplyJobAPIView,
    ApplyEligibilityAPIView,
    JobApplicantsAPIView,
    JobDashboardAPIView,
    JobDetailAPIView,
    JobListCreateAPIView,
    JobUpdateAPIView,
    MarkViewedJobAPIView,
    MyJobsAPIView,
    SaveJobAPIView,
)

app_name = "jobs"

urlpatterns = [
    path("", JobListCreateAPIView.as_view(), name="job-list-create"),
    path("dashboard/", JobDashboardAPIView.as_view(), name="job-dashboard"),
    path("my-jobs/", MyJobsAPIView.as_view(), name="my-jobs"),
    path("<int:id>/", JobDetailAPIView.as_view(), name="job-detail"),
    path("<int:id>/apply/", ApplyJobAPIView.as_view(), name="job-apply"),
    path("<int:id>/apply-eligibility/", ApplyEligibilityAPIView.as_view(), name="job-apply-eligibility"),
    path("<int:id>/view/", MarkViewedJobAPIView.as_view(), name="job-view"),
    path("<int:id>/save/", SaveJobAPIView.as_view(), name="job-save"),
    path("<int:id>/edit/", JobUpdateAPIView.as_view(), name="job-edit"),
    path("<int:id>/applicants/", JobApplicantsAPIView.as_view(), name="job-applicants"),
]
