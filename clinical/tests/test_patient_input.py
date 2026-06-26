"""Tests for patient self-entry and camera upload API."""
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from clinical.models import Observation, ObservationAttachment, PatientProfile, PatientUser, UserRole


def _make_test_image(name="test.jpg"):
    buf = BytesIO()
    Image.new("RGB", (100, 100), color=(120, 180, 200)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=__import__("tempfile").mkdtemp())
class PatientInputAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient = PatientUser.objects.create_user(
            username="input_patient",
            password="secure-password-123",
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(
            user=self.patient,
            given_name="Input",
            family_name="Patient",
        )
        self.client.force_authenticate(user=self.patient)

    def test_measurement_types(self):
        url = reverse("measurement-types")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data["measurement_types"]), 0)

    def test_submit_numeric_observation(self):
        url = reverse("observation-submit")
        response = self.client.post(
            url,
            {
                "loinc_code": "4548-4",
                "value_quantity": "6.1",
                "note": "Before breakfast",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Observation.objects.filter(patient=self.patient).count(), 1)

    def test_submit_with_camera_image(self):
        url = reverse("observation-submit")
        image = _make_test_image()
        response = self.client.post(
            url,
            {
                "loinc_code": "8480-6",
                "value_quantity": "128",
                "capture_source": "camera",
                "image": image,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Observation.objects.filter(patient=self.patient).count(), 1)
        self.assertEqual(ObservationAttachment.objects.filter(patient=self.patient).count(), 1)
