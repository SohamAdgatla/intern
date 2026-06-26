"""
Create a demo portal patient for testing Add Health Data + login.

Usage:
  python manage.py create_demo_patient
  python manage.py create_demo_patient --username jane --password 'MySecurePass123!'
"""
from django.core.management.base import BaseCommand

from clinical.models import PatientProfile, PatientUser, UserRole


class Command(BaseCommand):
    help = "Create a demo patient account for portal login and data entry."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo_patient")
        parser.add_argument("--password", default="DemoPatient123!")
        parser.add_argument("--given-name", default="Demo")
        parser.add_argument("--family-name", default="Patient")

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        user, created = PatientUser.objects.get_or_create(
            username=username,
            defaults={"role": UserRole.PATIENT, "email": f"{username}@example.com"},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created user '{username}'"))
        else:
            user.set_password(password)
            user.save()
            self.stdout.write(f"Updated password for existing user '{username}'")

        PatientProfile.objects.get_or_create(
            user=user,
            defaults={
                "given_name": options["given_name"],
                "family_name": options["family_name"],
            },
        )

        self.stdout.write(f"  Username: {username}")
        self.stdout.write(f"  Password: {password}")
        self.stdout.write("Sign in on the Add Health Data page to submit readings.")
