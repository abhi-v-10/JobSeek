from django.db import models
from django.contrib.auth.models import User


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

	status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
	posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="jobs")

	job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)

	# Corporate fields
	company = models.CharField(max_length=255, blank=True)
	position = models.CharField(max_length=255, blank=True)
	type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, blank=True)
	level = models.CharField(max_length=100, blank=True)

	# Domestic fields
	work = models.TextField(blank=True)
	daily_work_time = models.IntegerField(null=True, blank=True)
	hourly_wage = models.CharField(max_length=100, blank=True)

	# Common
	location = models.CharField(max_length=255)
	salary_min = models.IntegerField(null=True, blank=True)
	salary_max = models.IntegerField(null=True, blank=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.position or self.work} - {self.location}"
