from datetime import datetime, timedelta, timezone

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from clinical.models import (
    AdherenceStatus,
    CodeSystem,
    CodedConcept,
    MedicationStatement,
    Observation,
    ObservationCategory,
    PatientProfile,
    PatientUser,
    UserRole,
)
from clinical.services.ml_engine import LOINC_SYSTOLIC_BP
from clinical.services.smart_alerts import SmartAlertEngine


class SmartAlertEngineTests(TestCase):
    def setUp(self):
        self.patient = PatientUser.objects.create_user(
            username="alert_patient",
            password="secure-password-123",
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(user=self.patient, given_name="Alert", family_name="Test")

    def test_low_adherence_generates_alert(self):
        rx = CodedConcept.objects.create(system=CodeSystem.RXNORM, code="6809", display="Metformin")
        MedicationStatement.objects.create(
            patient=self.patient,
            medication_code=rx,
            period_start=datetime.now(tz=timezone.utc) - timedelta(days=30),
            adherence_status=AdherenceStatus.PARTIAL,
            adherence_percentage=55,
        )
        result = SmartAlertEngine(self.patient).evaluate()
        self.assertGreater(result["alert_count"], 0)
        self.assertTrue(any(a["category"] == "medication" for a in result["alerts"]))

    def test_rising_bp_generates_watch_alert(self):
        code = CodedConcept.objects.create(
            system=CodeSystem.LOINC, code=LOINC_SYSTOLIC_BP, display="Systolic BP"
        )
        base = datetime.now(tz=timezone.utc) - timedelta(days=200)
        for i, val in enumerate([118, 125, 132, 138, 142]):
            Observation.objects.create(
                patient=self.patient,
                code=code,
                category=ObservationCategory.VITAL_SIGNS,
                value_quantity=val,
                value_unit="mmHg",
                effective_datetime=base + timedelta(days=40 * i),
            )
        result = SmartAlertEngine(self.patient).evaluate()
        self.assertTrue(any(a["id"] == "bp-rising-6m" for a in result["alerts"]))


class SmartAlertsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient = PatientUser.objects.create_user(
            username="alert_api",
            password="secure-password-123",
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(user=self.patient, given_name="Api", family_name="Alert")
        self.client.force_authenticate(user=self.patient)

    def test_alerts_endpoint(self):
        response = self.client.get(reverse("alerts"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("alerts", response.data)
