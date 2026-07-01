"""
Application Management System — API Integration Tests

Verifies CRUD operations, nested routes, custom endpoints, analytics,
filtering, searching, pagination, and signal reactions.
"""

from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.jobs.models import Job
from ..models import JobApplication, ApplicationTimeline, ApplicationNote, InterviewRound, Offer
from ..constants import ApplicationStatus, InterviewType, InterviewStatus, TimelineEventType

User = get_user_model()


class APIIntegrationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="candidate",
            email="candidate@example.com",
            password="testpassword"
        )
        self.other_user = User.objects.create_user(
            username="other_candidate",
            email="other@example.com",
            password="testpassword"
        )
        self.poster = User.objects.create_user(
            username="poster",
            email="poster@example.com",
            password="testpassword"
        )
        
        # Create profile for user
        # Note: users/signals.py should auto-create Profile, but we can verify/ensure it
        from apps.users.models import Profile
        Profile.objects.get_or_create(user=self.user)
        
        self.job = Job.objects.create(
            status="open",
            posted_by=self.poster,
            job_type="corporate",
            company="Google",
            position="Software Engineer",
            location="Mountain View, CA"
        )
        self.job_two = Job.objects.create(
            status="open",
            posted_by=self.poster,
            job_type="corporate",
            company="Facebook",
            position="Product Manager",
            location="Menlo Park, CA"
        )

        self.client.force_authenticate(user=self.user)

    # ── JobApplication CRUD Tests ───────────────────────────────────────────

    def test_create_application_api(self):
        url = "/api/applications/"
        data = {
            "job": self.job.id,
            "cover_letter": "I love Google.",
            "notes": "Referral from John",
            "expected_salary": "150000.00",
            "source": "linkedin",
            "status": "draft"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "draft")
        
        # Verify timeline auto-creation signal
        app_id = response.data["id"]
        timeline_count = ApplicationTimeline.objects.filter(application_id=app_id).count()
        self.assertEqual(timeline_count, 1)

    def test_list_applications_api(self):
        JobApplication.objects.create(user=self.user, job=self.job)
        JobApplication.objects.create(user=self.user, job=self.job_two)
        
        url = "/api/applications/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify pagination
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 2)

    def test_retrieve_application_api(self):
        app = JobApplication.objects.create(user=self.user, job=self.job)
        url = f"/api/applications/{app.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["job"]["id"], self.job.id)

    def test_update_application_status_api(self):
        app = JobApplication.objects.create(user=self.user, job=self.job, status=ApplicationStatus.DRAFT)
        url = f"/api/applications/{app.id}/"
        
        # Attempt an invalid transition (draft -> applied is invalid directly without ready_to_apply)
        response = self.client.patch(url, {"status": "applied"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Valid transition (draft -> ready_to_apply)
        response = self.client.patch(url, {"status": "ready_to_apply"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ready_to_apply")

    def test_soft_delete_application_api(self):
        app = JobApplication.objects.create(user=self.user, job=self.job)
        url = f"/api/applications/{app.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify it is archived (soft deleted) but still in database
        app.refresh_from_db()
        self.assertTrue(app.archived)

    # ── Nested Resources Tests ──────────────────────────────────────────────

    def test_timeline_nested_api(self):
        app = JobApplication.objects.create(user=self.user, job=self.job)
        url = f"/api/applications/{app.id}/timeline/"
        
        # List timeline (should have 1 auto-created event)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Create custom timeline event
        data = {
            "event_type": "custom",
            "description": "Followed up with HR today."
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["event_type"], "custom")

    def test_notes_nested_api(self):
        app = JobApplication.objects.create(user=self.user, job=self.job)
        url = f"/api/applications/{app.id}/notes/"
        
        # Create note
        response = self.client.post(url, {"note": "HR recruiter was super friendly."})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        note_id = response.data["id"]

        # List notes
        response = self.client.get(url)
        self.assertEqual(len(response.data), 1)

        # Delete note
        response = self.client.delete(f"{url}{note_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_interviews_nested_api(self):
        app = JobApplication.objects.create(user=self.user, job=self.job)
        url = f"/api/applications/{app.id}/interviews/"
        
        # Create interview round
        data = {
            "round_number": 1,
            "interview_type": "technical",
            "scheduled_time": timezone.now() + timezone.timedelta(days=2),
            "interviewer": "Senior Engineer",
            "location": "https://zoom.us/j/12345"
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["round_number"], 1)

    def test_offer_nested_api(self):
        app = JobApplication.objects.create(user=self.user, job=self.job)
        url = f"/api/applications/{app.id}/offer/"
        
        # Create offer
        data = {
            "base_salary": "120000.00",
            "location": "Austin, TX",
            "remote": True
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["base_salary"], "120000.00")

    # ── Custom Analytics / Dashboard Endpoints ──────────────────────────────

    def test_dashboard_endpoint(self):
        app = JobApplication.objects.create(user=self.user, job=self.job, status="offer_accepted")
        Offer.objects.create(application=app, base_salary=140000)
        
        url = "/api/applications/dashboard/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_applications"], 1)
        self.assertEqual(response.data["success_rate"], 100.0)

    def test_upcoming_interviews_endpoint(self):
        app = JobApplication.objects.create(user=self.user, job=self.job)
        InterviewRound.objects.create(
            application=app,
            round_number=1,
            interview_type="technical",
            scheduled_time=timezone.now() + timezone.timedelta(days=1),
            status="scheduled"
        )
        
        url = "/api/applications/upcoming-interviews/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_follow_ups_endpoint(self):
        app = JobApplication.objects.create(
            user=self.user, 
            job=self.job, 
            status="applied"
        )
        # Manually backdate updated_at using queryset.update to bypass auto_now
        JobApplication.objects.filter(id=app.id).update(
            updated_at=timezone.now() - timezone.timedelta(days=10)
        )
        
        url = "/api/applications/follow-ups/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_analytics_endpoint(self):
        JobApplication.objects.create(user=self.user, job=self.job, status="offer_accepted")
        url = "/api/applications/analytics/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("application_trend", response.data)
        self.assertIn("response_rate", response.data)
