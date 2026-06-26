"""Tests for the Health Story rule engine and API."""
from datetime import datetime, timedelta, timezone

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from clinical.models import (
    CodeSystem,
    CodedConcept,
    Observation,
    ObservationCategory,
    PatientProfile,
    PatientUser,
    UserRole,
)
from clinical.services.health_story import HealthStoryEngine
from clinical.services.ml_engine import LOINC_LDL


class HealthStoryEngineTests(TestCase):
    def setUp(self):
        self.patient = PatientUser.objects.create_user(
            username="story_patient",
            password="secure-password-123",
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(
            user=self.patient,
            given_name="Story",
            family_name="Patient",
        )
        self.ldl_code = CodedConcept.objects.create(
            system=CodeSystem.LOINC,
            code=LOINC_LDL,
            display="LDL Cholesterol",
        )

    def _add_ldl(self, days_ago: int, value: float) -> None:
        Observation.objects.create(
            patient=self.patient,
            code=self.ldl_code,
            category=ObservationCategory.LABORATORY,
            value_quantity=value,
            value_unit="mg/dL",
            reference_low=0,
            reference_high=100,
            effective_datetime=datetime.now(tz=timezone.utc) - timedelta(days=days_ago),
        )

    def test_ldl_fifteen_percent_drop_over_six_months(self):
        self._add_ldl(180, 120.0)
        self._add_ldl(0, 102.0)

        result = HealthStoryEngine(self.patient, lookback_months=12).generate()
        ldl_story = next(h for h in result.highlights if h.loinc_code == LOINC_LDL)

        self.assertEqual(ldl_story.change.direction, "improving")
        self.assertAlmostEqual(ldl_story.change.percent_change, -15.0, places=0)
        self.assertIn("come down", ldl_story.narrative.lower())
        self.assertEqual(ldl_story.tone, "positive")

    def test_stable_biomarker_uses_steady_language(self):
        self._add_ldl(200, 110.0)
        self._add_ldl(0, 111.0)

        result = HealthStoryEngine(self.patient, lookback_months=12).generate()
        ldl_story = next(h for h in result.highlights if h.loinc_code == LOINC_LDL)

        self.assertEqual(ldl_story.change.direction, "stable")
        self.assertIn("steady", ldl_story.narrative.lower())

    def test_result_has_headline_and_encouragement(self):
        self._add_ldl(180, 130.0)
        self._add_ldl(0, 100.0)

        result = HealthStoryEngine(self.patient, lookback_months=24).generate()

        self.assertTrue(result.headline)
        self.assertTrue(result.overview)
        self.assertTrue(result.encouragement)
        self.assertGreaterEqual(len(result.paragraphs), 1)


class HealthStoryAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient = PatientUser.objects.create_user(
            username="story_api_patient",
            password="secure-password-123",
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(
            user=self.patient,
            given_name="Api",
            family_name="Story",
        )
        self.client.force_authenticate(user=self.patient)

        code = CodedConcept.objects.create(
            system=CodeSystem.LOINC,
            code=LOINC_LDL,
            display="LDL Cholesterol",
        )
        Observation.objects.create(
            patient=self.patient,
            code=code,
            category=ObservationCategory.LABORATORY,
            value_quantity=100,
            value_unit="mg/dL",
            reference_low=0,
            reference_high=100,
            effective_datetime=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        Observation.objects.create(
            patient=self.patient,
            code=code,
            category=ObservationCategory.LABORATORY,
            value_quantity=85,
            value_unit="mg/dL",
            reference_low=0,
            reference_high=100,
            effective_datetime=datetime(2024, 7, 1, tzinfo=timezone.utc),
        )

    def test_health_story_endpoint_returns_200(self):
        url = reverse("health-story")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["patient_id"], self.patient.id)
        self.assertIn("headline", response.data)
        self.assertIn("highlights", response.data)

    def test_invalid_lookback_months_rejected(self):
        url = reverse("health-story")
        response = self.client.get(url, {"lookback_months": "3"})
        self.assertEqual(response.status_code, 400)
