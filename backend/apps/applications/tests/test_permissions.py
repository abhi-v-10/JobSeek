"""
Application Management System — Permission Tests

Verifies owner-only access permissions and staff/admin override access.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from apps.jobs.models import Job
from ..models import JobApplication, ApplicationNote
from ..permissions import IsApplicationOwner

User = get_user_model()


class PermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsApplicationOwner()
        
        self.user_a = User.objects.create_user(
            username="user_a",
            email="usera@example.com",
            password="testpassword"
        )
        self.user_b = User.objects.create_user(
            username="user_b",
            email="userb@example.com",
            password="testpassword"
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="testpassword"
        )
        self.poster = User.objects.create_user(
            username="poster",
            email="poster@example.com",
            password="testpassword"
        )
        
        self.job = Job.objects.create(
            status="open",
            posted_by=self.poster,
            job_type="corporate",
            company="Test Company",
            position="Test Position",
            location="Test Location"
        )
        
        self.app_a = JobApplication.objects.create(user=self.user_a, job=self.job)
        self.note_a = ApplicationNote.objects.create(
            application=self.app_a,
            author=self.user_a,
            note="Note A"
        )

    def test_application_owner_allowed(self):
        request = self.factory.get("/")
        request.user = self.user_a
        
        # Owner of the application should have permission
        has_perm = self.permission.has_object_permission(request, None, self.app_a)
        self.assertTrue(has_perm)
        
        # Owner of the parent application should have permission on nested resources
        has_perm = self.permission.has_object_permission(request, None, self.note_a)
        self.assertTrue(has_perm)

    def test_non_owner_denied(self):
        request = self.factory.get("/")
        request.user = self.user_b
        
        # Non-owner should be denied permission
        has_perm = self.permission.has_object_permission(request, None, self.app_a)
        self.assertFalse(has_perm)
        
        has_perm = self.permission.has_object_permission(request, None, self.note_a)
        self.assertFalse(has_perm)

    def test_staff_bypass_allowed(self):
        request = self.factory.get("/")
        request.user = self.admin
        
        # Admin staff should bypass permission check
        has_perm = self.permission.has_object_permission(request, None, self.app_a)
        self.assertTrue(has_perm)
        
        has_perm = self.permission.has_object_permission(request, None, self.note_a)
        self.assertTrue(has_perm)
