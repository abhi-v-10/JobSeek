from django.db import models
from django.conf import settings


class Job(models.Model):
	JOB_TYPE_CHOICES = (
		("corporate", "Corporate"),
		("domestic", "Domestic"),
	)

	EMPLOYMENT_TYPE_CHOICES = (
		("full_time", "Full Time"),
		("part_time", "Part Time"),
	)
	STATUS_CHOICES = (
		("open", "Open"),
		("closed", "Closed"),
	)

	WORK_MODE_CHOICES = (
		("onsite", "On-site"),
		("remote", "Remote / Work from Home"),
		("hybrid", "Hybrid"),
	)

	status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
	posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jobs")

	job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)

	# Corporate fields
	company = models.CharField(max_length=255, blank=True)
	position = models.CharField(max_length=255, blank=True)
	type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, blank=True)
	required_experience_years = models.PositiveIntegerField(null=True, blank=True, help_text="Minimum years of experience required")
	required_experience_fields = models.TextField(blank=True, help_text="Comma-separated fields/tech stack (e.g. React, Django, PostgreSQL)")

	# Domestic fields
	work = models.TextField(blank=True)
	daily_work_time = models.IntegerField(null=True, blank=True)
	hourly_wage = models.CharField(max_length=100, blank=True)

	# Common
	location = models.CharField(max_length=255)
	salary_min = models.IntegerField(null=True, blank=True)
	salary_max = models.IntegerField(null=True, blank=True)
	description = models.TextField(blank=True, help_text="Full job description")
	work_mode = models.CharField(max_length=20, choices=WORK_MODE_CHOICES, default="onsite")

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.position or self.work} - {self.location}"


class JobApplication(models.Model):
	STATUS_APPLIED = "applied"
	STATUS_REVIEWING = "reviewing"
	STATUS_REJECTED = "rejected"
	STATUS_ACCEPTED = "accepted"

	STATUS_CHOICES = (
		(STATUS_APPLIED, "Applied"),
		(STATUS_REVIEWING, "Reviewing"),
		(STATUS_REJECTED, "Rejected"),
		(STATUS_ACCEPTED, "Accepted"),
	)

	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="job_applications",
	)
	job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_APPLIED)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["user", "job"], name="unique_job_application_per_user"),
		]
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.user_id} applied to {self.job_id}"


class ViewedJob(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="viewed_jobs",
	)
	job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="view_records")
	viewed_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["user", "job"], name="unique_job_view_per_user"),
		]
		ordering = ["-viewed_at"]

	def __str__(self):
		return f"{self.user_id} viewed {self.job_id}"


class SavedJob(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="saved_jobs",
	)
	job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="saved_by_users")
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["user", "job"], name="unique_saved_job_per_user"),
		]
		ordering = ["-created_at"]

	def __str__(self):
		return f"{self.user_id} saved {self.job_id}"


class JobInteractionStats(models.Model):
	job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="interaction_stats")
	applied_count = models.PositiveIntegerField(default=0)
	viewed_count = models.PositiveIntegerField(default=0)
	saved_count = models.PositiveIntegerField(default=0)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Stats for job {self.job_id}"
