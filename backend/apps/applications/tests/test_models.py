"""
Application Management System — Model Tests

Verifies model creation, constraints, relationships, properties,
and string representations.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from apps.jobs.models import Job
from ..models import JobApplication, ApplicationTimeline, ApplicationNote, InterviewRound, Offer
from ..constants import ApplicationStatus, InterviewType, InterviewStatus, TimelineEventType

User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        # Create user
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
        
        # Create job
        self.job = Job.objects.create(
            status="open",
            posted_by=self.poster,
            job_type="corporate",
            company="Test Company",
            position="Test Position",
            location="Test Location"
        )

    def test_job_application_creation_and_properties(self):
        application = JobApplication.objects.create(
            user=self.user,
            job=self.job,
            status=ApplicationStatus.DRAFT,
            notes="Initial notes"
        )
        self.assertEqual(application.status, ApplicationStatus.DRAFT)
        self.assertTrue(application.is_active)
        self.assertFalse(application.is_interviewing)
        self.assertFalse(application.has_offer)
        self.assertIn("candidate", str(application))

    def test_unique_application_constraint(self):
        JobApplication.objects.create(user=self.user, job=self.job)
        with self.assertRaises(IntegrityError):
            JobApplication.objects.create(user=self.user, job=self.job)

    def test_application_timeline_creation(self):
        application = JobApplication.objects.create(user=self.user, job=self.job)
        timeline = ApplicationTimeline.objects.create(
            application=application,
            event_type=TimelineEventType.CREATED,
            description="Created application"
        )
        self.assertEqual(timeline.event_type, TimelineEventType.CREATED)
        self.assertEqual(timeline.description, "Created application")

    def test_application_note_creation(self):
        application = JobApplication.objects.create(user=self.user, job=self.job)
        note = ApplicationNote.objects.create(
            application=application,
            author=self.user,
            note="This is a test note."
        )
        self.assertEqual(note.note, "This is a test note.")

    def test_interview_round_creation_and_constraints(self):
        application = JobApplication.objects.create(user=self.user, job=self.job)
        round_1 = InterviewRound.objects.create(
            application=application,
            round_number=1,
            interview_type=InterviewType.TECHNICAL,
            status=InterviewStatus.SCHEDULED
        )
        self.assertEqual(round_1.round_number, 1)
        self.assertEqual(round_1.interview_type, InterviewType.TECHNICAL)

        # Unique constraint on round_number per application
        with self.assertRaises(IntegrityError):
            InterviewRound.objects.create(
                application=application,
                round_number=1,
                interview_type=InterviewType.HR
            )

    def test_offer_creation(self):
        application = JobApplication.objects.create(user=self.user, job=self.job)
        offer = Offer.objects.create(
            application=application,
            base_salary=100000.00,
            remote=True
        )
        self.assertEqual(offer.base_salary, 100000.00)
        self.assertTrue(offer.remote)
