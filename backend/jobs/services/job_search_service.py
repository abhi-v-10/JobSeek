from django.db.models import Q
from jobs.models import Job


def search_jobs(filters):
    # Only return open jobs by default
    queryset = Job.objects.filter(status="open")

    if filters.get("job_type"):
        queryset = queryset.filter(job_type=filters["job_type"])

    if filters.get("role"):
        role_query = filters["role"]
        queryset = queryset.filter(
            Q(position__icontains=role_query) | Q(work__icontains=role_query)
        )

    if filters.get("skills"):
        queryset = queryset.filter(
            required_experience_fields__icontains=filters["skills"]
        )

    if filters.get("location"):
        queryset = queryset.filter(location__icontains=filters["location"])

    if filters.get("remote"):
        # Map remote boolean to work_mode string
        is_remote = filters["remote"]
        if is_remote in ["true", "True", "1", True]:
            queryset = queryset.filter(work_mode="remote")

    # Salary filtering: job salary range overlaps with requested range
    salary_min_param = filters.get("salary_min")
    salary_max_param = filters.get("salary_max")

    if salary_min_param is not None or salary_max_param is not None:
        try:
            if salary_min_param is not None:
                salary_min = int(salary_min_param)
                # Job's max salary must be >= requested min salary
                # Or job has no max salary but min salary >= requested min salary
                queryset = queryset.filter(
                    Q(salary_max__gte=salary_min)
                    | Q(salary_max__isnull=True, salary_min__gte=salary_min)
                )

            if salary_max_param is not None:
                salary_max = int(salary_max_param)
                # Job's min salary must be <= requested max salary
                # Or job has no min salary
                queryset = queryset.filter(
                    Q(salary_min__lte=salary_max) | Q(salary_min__isnull=True)
                )
        except (ValueError, TypeError):
            # Ignore invalid salary format
            pass

    return queryset
