from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.users.models import Profile
from apps.jobs.models import Job
from apps.applications.models import JobApplication
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class JobApplicationIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Create a poster
        self.poster = User.objects.create_user(username="poster", email="poster@test.com", password="password123")
        Profile.objects.filter(user=self.poster).update(user_type="poster")
        
        # Create a job
        self.job = Job.objects.create(
            posted_by=self.poster,
            position="Software Engineer",
            job_type="corporate",
            company="TestCorp",
            location="Remote"
        )
        
        # Create an applicant
        self.applicant = User.objects.create_user(username="applicant", email="applicant@test.com", password="password123")
        dummy_resume = SimpleUploadedFile("dummy.pdf", b"dummy content", content_type="application/pdf")
        
        # Profile is created by signal, so we update it
        profile = self.applicant.profile
        profile.user_type = "applicant"
        profile.resume = dummy_resume
        profile.linkedin_url = "http://linkedin.com"
        profile.github_url = "http://github.com"
        profile.save()
        
    def test_apply_flow_creates_new_application_record(self):
        # 1. Authenticate as applicant
        self.client.force_authenticate(user=self.applicant)
        
        # 2. Check initial count
        self.assertEqual(JobApplication.objects.count(), 0)
        
        # 3. Apply for the job via the jobs app API
        url = reverse("jobs:job-apply", kwargs={"id": self.job.id})
        response = self.client.post(url, {"consent": True})
        
        # 4. Verify successful application
        if response.status_code != 201:
            print("Response:", response.data)
        self.assertEqual(response.status_code, 201)
        self.assertIn("application", response.data)
        
        # 5. Verify the JobApplication record exists in the new applications app
        self.assertEqual(JobApplication.objects.count(), 1)
        app = JobApplication.objects.first()
        self.assertEqual(app.user, self.applicant)
        self.assertEqual(app.job, self.job)
        
        # 6. Verify the applications dashboard also sees it
        dashboard_url = "/api/applications/dashboard/"
        dash_response = self.client.get(dashboard_url)
        self.assertEqual(dash_response.status_code, 200)
        self.assertEqual(dash_response.data["total_applications"], 1)
        self.assertEqual(dash_response.data["by_status"]["applied"], 1)
