"""Tests for the Timeline Aggregator service and API."""
from datetime import datetime, timedelta, timezone

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from clinical.models import (
    CodeSystem,
    CodedConcept,
    Condition,
    ConditionClinicalStatus,
    MedicationStatement,
    Observation,
    ObservationCategory,
    PatientProfile,
    PatientUser,
    UserRole,
)
from clinical.services.timeline_aggregator import TimelineAggregator, parse_timeline_query_params


class TimelineAggregatorServiceTests(TestCase):
    def setUp(self):
        self.patient = PatientUser.objects.create_user(
            username="timeline_patient",
            password="secure-password-123",
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(
            user=self.patient,
            given_name="Jane",
            family_name="Doe",
        )

        self.loinc_hba1c = CodedConcept.objects.create(
            system=CodeSystem.LOINC,
            code="4548-4",
            display="HbA1c",
        )
        self.snomed_diabetes = CodedConcept.objects.create(
            system=CodeSystem.SNOMED,
            code="44054006",
            display="Type 2 diabetes mellitus",
        )
        self.rx_metformin = CodedConcept.objects.create(
            system=CodeSystem.RXNORM,
            code="6809",
            display="Metformin",
        )

        base = datetime(2022, 6, 1, 9, 0, tzinfo=timezone.utc)

        Observation.objects.create(
            patient=self.patient,
            code=self.loinc_hba1c,
            category=ObservationCategory.LABORATORY,
            value_quantity=6.8,
            value_unit="%",
            reference_low=4.0,
            reference_high=5.6,
            effective_datetime=base,
        )
        Observation.objects.create(
            patient=self.patient,
            code=self.loinc_hba1c,
            category=ObservationCategory.LABORATORY,
            value_quantity=6.2,
            value_unit="%",
            reference_low=4.0,
            reference_high=5.6,
            effective_datetime=base + timedelta(days=180),
        )

        Condition.objects.create(
            patient=self.patient,
            code=self.snomed_diabetes,
            clinical_status=ConditionClinicalStatus.ACTIVE,
            onset_datetime=base + timedelta(days=30),
        )

        MedicationStatement.objects.create(
            patient=self.patient,
            medication_code=self.rx_metformin,
            period_start=base + timedelta(days=45),
            adherence_percentage=85,
        )

        self.other_patient = PatientUser.objects.create_user(
            username="other_patient",
            password="secure-password-123",
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(
            user=self.other_patient,
            given_name="Other",
            family_name="Person",
        )

    def test_aggregate_sorts_oldest_to_newest(self):
        result = TimelineAggregator(self.patient).aggregate()

        self.assertEqual(result["total_events"], 4)
        self.assertEqual(result["patient_id"], self.patient.id)

        sort_times = [e["sort_datetime"] for e in result["events"]]
        self.assertEqual(sort_times, sorted(sort_times))

        self.assertEqual(result["events"][0]["resource_type"], "observation")
        self.assertEqual(result["events"][0]["title"], "HbA1c")
        self.assertEqual(result["events"][1]["resource_type"], "condition")
        self.assertEqual(result["events"][2]["resource_type"], "medication")
        self.assertEqual(result["events"][3]["resource_type"], "observation")

    def test_filter_by_resource_types(self):
        from clinical.services.timeline_aggregator import TimelineQueryParams

        params = TimelineQueryParams(resource_types={"observation"})
        result = TimelineAggregator(self.patient, params).aggregate()
        self.assertEqual(result["total_events"], 2)
        self.assertTrue(all(e["resource_type"] == "observation" for e in result["events"]))

    def test_parse_invalid_types_raises(self):
        with self.assertRaises(ValueError):
            parse_timeline_query_params({"types": "observation,invalid"})


class TimelineAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient = PatientUser.objects.create_user(
            username="api_patient",
            password="secure-password-123",
            role=UserRole.PATIENT,
        )
        PatientProfile.objects.create(
            user=self.patient,
            given_name="Api",
            family_name="Patient",
        )
        self.client.force_authenticate(user=self.patient)

        code = CodedConcept.objects.create(
            system=CodeSystem.LOINC,
            code="8480-6",
            display="Systolic blood pressure",
        )
        Observation.objects.create(
            patient=self.patient,
            code=code,
            category=ObservationCategory.VITAL_SIGNS,
            value_quantity=128,
            value_unit="mmHg",
            reference_low=90,
            reference_high=120,
            effective_datetime=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )

    def test_timeline_endpoint_returns_200(self):
        url = reverse("timeline")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["patient_id"], self.patient.id)
        self.assertEqual(len(response.data["events"]), 1)
        self.assertEqual(response.data["events"][0]["resource_type"], "observation")

    def test_patient_cannot_access_other_patient_id(self):
        url = reverse("timeline")
        response = self.client.get(url, {"patient_id": "999"})
        self.assertEqual(response.status_code, 403)
