"""Tests for patient signup and login flows."""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from clinical.models import PatientProfile, PatientUser, UserRole


class AuthSignupTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_signup_creates_patient_and_profile(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "newpatient",
                "password": "StrongPass123!",
                "given_name": "New",
                "family_name": "Patient",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(PatientUser.objects.filter(username="newpatient").exists())
        user = PatientUser.objects.get(username="newpatient")
        self.assertEqual(user.role, UserRole.PATIENT)
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertEqual(user.profile.given_name, "New")
        self.assertEqual(user.profile.family_name, "Patient")
        self.assertEqual(response.data["given_name"], "New")
        self.assertEqual(response.data["family_name"], "Patient")
        self.assertEqual(response.data["full_name"], "New Patient")

    def test_signup_rejects_duplicate_username(self):
        PatientUser.objects.create_user(
            username="existinguser",
            password="StrongPass123!",
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(
            user=PatientUser.objects.get(username="existinguser"),
            given_name="Existing",
            family_name="User",
        )

        response = self.client.post(
            reverse("signup"),
            {
                "username": "existinguser",
                "password": "AnotherStrongPass123!",
                "given_name": "Duplicate",
                "family_name": "User",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.data["detail"].lower())

    def test_authenticated_user_can_read_and_update_profile(self):
        user = PatientUser.objects.create_user(
            username="profileuser",
            password="StrongPass123!",
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(
            user=user,
            given_name="Profile",
            family_name="User",
            phone="555-0100",
            email_contact="profile@example.com",
        )
        self.client.force_authenticate(user=user)

        get_response = self.client.get(reverse("profile"))
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["full_name"], "Profile User")

        patch_response = self.client.patch(
            reverse("profile"),
            {"given_name": "Updated", "phone": "555-0200"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        user.refresh_from_db()
        user.profile.refresh_from_db()
        self.assertEqual(user.profile.given_name, "Updated")
        self.assertEqual(user.profile.phone, "555-0200")
