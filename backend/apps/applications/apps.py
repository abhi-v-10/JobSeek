"""
Application Management System — App Configuration

Registers the applications app with Django and loads signals
on app startup to enable automatic timeline event creation.
"""

from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    """Django app configuration for the Application Management System."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.applications"
    label = "applications"
    verbose_name = "Application Management"

    def ready(self) -> None:
        """Import signals module to register signal handlers on startup."""
        import apps.applications.signals  # noqa: F401
