"""
Application Management System — Validator Tests

Verifies status transition state machine rules and duplicate application prevention.
"""

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.jobs.models import Job
from ..models import JobApplication
from ..validators import validate_status_transition, validate_unique_application
from ..constants import ApplicationStatus

User = get_user_model()


class ValidatorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="candidate",
            email="candidate@example.com",
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

    def test_valid_status_transitions(self):
        # Setting the same status is always allowed
        validate_status_transition(ApplicationStatus.DRAFT, ApplicationStatus.DRAFT)
        
        # Valid draft transitions
        validate_status_transition(ApplicationStatus.DRAFT, ApplicationStatus.READY_TO_APPLY)
        validate_status_transition(ApplicationStatus.DRAFT, ApplicationStatus.WITHDRAWN)
        
        # Valid applied transitions
        validate_status_transition(ApplicationStatus.APPLIED, ApplicationStatus.UNDER_REVIEW)
        validate_status_transition(ApplicationStatus.APPLIED, ApplicationStatus.REJECTED)

    def test_invalid_status_transitions(self):
        # Invalid draft transitions
        with self.assertRaises(ValidationError):
            validate_status_transition(ApplicationStatus.DRAFT, ApplicationStatus.APPLIED)

        # Terminal state transitions
        with self.assertRaises(ValidationError):
            validate_status_transition(ApplicationStatus.REJECTED, ApplicationStatus.OFFER_RECEIVED)
            
        with self.assertRaises(ValidationError):
            validate_status_transition(ApplicationStatus.WITHDRAWN, ApplicationStatus.APPLIED)

    def test_duplicate_application_validator(self):
        # No application exists yet
        validate_unique_application(self.user.id, self.job.id)
        
        # Create application
        JobApplication.objects.create(user=self.user, job=self.job)
        
        # Now validator should raise ValidationError
        with self.assertRaises(ValidationError):
            validate_unique_application(self.user.id, self.job.id)
            
        # Excluded instance should pass (useful for updates)
        app = JobApplication.objects.get(user=self.user, job=self.job)
        validate_unique_application(self.user.id, self.job.id, instance_id=app.id)
