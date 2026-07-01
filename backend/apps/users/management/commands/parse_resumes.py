"""
Management command to parse/re-parse resume text for all profiles with a resume file.

Usage:
    python manage.py parse_resumes          # Parse only unparsed resumes
    python manage.py parse_resumes --all    # Re-parse all resumes (including already parsed)
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.users.models import Profile
from apps.users.utils.resume_parser import extract_resume_text


class Command(BaseCommand):
    help = "Extract and store text from uploaded PDF resumes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Re-parse all resumes, including those already parsed",
        )

    def handle(self, *args, **options):
        reparse_all = options["all"]

        profiles = Profile.objects.exclude(resume="").exclude(resume__isnull=True)

        if not reparse_all:
            profiles = profiles.filter(resume_text__isnull=True)

        total = profiles.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("No resumes to parse."))
            return

        self.stdout.write(f"Parsing {total} resume(s)...")

        success = 0
        failed = 0

        for profile in profiles:
            try:
                text = extract_resume_text(profile.resume.path)
                profile.resume_text = text
                profile.resume_last_parsed_at = timezone.now()
                profile.save(update_fields=["resume_text", "resume_last_parsed_at"])
                success += 1
                self.stdout.write(f"  ✓ {profile.user.username} — {len(text)} chars")
            except (ValueError, Exception) as exc:
                failed += 1
                self.stderr.write(f"  ✗ {profile.user.username} — {exc}")

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. Parsed: {success}, Failed: {failed}")
        )
