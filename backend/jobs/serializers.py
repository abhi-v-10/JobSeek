from rest_framework import serializers

from .models import Job


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id",
            "status",
            "posted_by",
            "job_type",
            "company",
            "position",
            "type",
            "level",
            "work",
            "daily_work_time",
            "hourly_wage",
            "location",
            "salary_min",
            "salary_max",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "posted_by"]
