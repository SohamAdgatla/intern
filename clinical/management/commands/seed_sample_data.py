"""
Seed realistic longitudinal sample data for the health dashboard demo.

Creates (or reuses) a demo patient and populates:
  - CodedConcepts (LOINC vitals + labs, SNOMED conditions, RxNorm meds)
  - Observations   (2 years of vitals + quarterly labs)
  - Conditions     (active diagnoses on the problem list)
  - MedicationStatements (current + past medications)

Usage:
  python manage.py seed_sample_data
  python manage.py seed_sample_data --username demo_patient --password DemoPatient123!
  python manage.py seed_sample_data --clear   # wipe existing clinical data first
"""
from __future__ import annotations

import random
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from clinical.models import (
    AdherenceStatus,
    CodeSystem,
    CodedConcept,
    Condition,
    ConditionClinicalStatus,
    ConditionVerificationStatus,
    MedicationStatement,
    MedicationStatus,
    Observation,
    ObservationCategory,
    ObservationStatus,
    PatientProfile,
    PatientUser,
    UserRole,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _concept(system: str, code: str, display: str) -> CodedConcept:
    """Get-or-create a CodedConcept row (idempotent)."""
    obj, _ = CodedConcept.objects.get_or_create(
        system=system,
        code=code,
        version="",
        defaults={"display": display},
    )
    return obj


def _dt(days_ago: int, hour: int = 8):
    """Return an aware datetime N days in the past at a given hour."""
    return timezone.now().replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(
        days=days_ago
    )


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Seed realistic longitudinal sample clinical data for the demo patient."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo_patient")
        parser.add_argument("--password", default="DemoPatient123!")
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing observations, conditions, and medications for the demo patient before seeding.",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        # 1. Ensure patient user + profile exist
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
            self.stdout.write(f"Reusing existing user '{username}'")

        PatientProfile.objects.get_or_create(
            user=user,
            defaults={
                "given_name": "Alex",
                "family_name": "Rivera",
                "birth_date": date(1978, 4, 15),
                "gender": "male",
                "phone": "+1-555-0142",
                "email_contact": "alex.rivera@example.com",
                "address_line": "742 Evergreen Terrace",
                "city": "Springfield",
                "state": "IL",
                "postal_code": "62704",
                "primary_care_provider": "Dr. Meredith Hayes, MD",
            },
        )

        # 2. Optionally clear existing clinical data
        if options["clear"]:
            obs_count, _ = Observation.objects.filter(patient=user).delete()
            cond_count, _ = Condition.objects.filter(patient=user).delete()
            med_count, _ = MedicationStatement.objects.filter(patient=user).delete()
            self.stdout.write(
                f"Cleared {obs_count} observations, {cond_count} conditions, "
                f"{med_count} medications."
            )

        # 3. Seed CodedConcepts
        # Vitals (LOINC)
        bp_sys   = _concept(CodeSystem.LOINC, "8480-6",  "Systolic blood pressure")
        bp_dia   = _concept(CodeSystem.LOINC, "8462-4",  "Diastolic blood pressure")
        hr       = _concept(CodeSystem.LOINC, "8867-4",  "Heart rate")
        weight   = _concept(CodeSystem.LOINC, "29463-7", "Body weight")
        height   = _concept(CodeSystem.LOINC, "8302-2",  "Body height")
        bmi      = _concept(CodeSystem.LOINC, "39156-5", "BMI")

        # Labs (LOINC)
        glucose  = _concept(CodeSystem.LOINC, "2339-0",  "Glucose [Mass/volume] in Blood")
        hba1c    = _concept(CodeSystem.LOINC, "4548-4",  "Hemoglobin A1c/Hemoglobin.total in Blood")
        chol     = _concept(CodeSystem.LOINC, "2093-3",  "Cholesterol [Mass/volume] in Serum or Plasma")
        hdl      = _concept(CodeSystem.LOINC, "2085-9",  "HDL Cholesterol")
        ldl      = _concept(CodeSystem.LOINC, "2089-1",  "LDL Cholesterol")
        trig     = _concept(CodeSystem.LOINC, "2571-8",  "Triglycerides")
        creat    = _concept(CodeSystem.LOINC, "2160-0",  "Creatinine [Mass/volume] in Serum or Plasma")
        egfr     = _concept(CodeSystem.LOINC, "62238-1", "eGFR")
        tsh      = _concept(CodeSystem.LOINC, "3016-3",  "TSH")

        # Conditions (SNOMED)
        t2dm_snomed = _concept(CodeSystem.SNOMED, "44054006",  "Type 2 diabetes mellitus")
        htn_snomed  = _concept(CodeSystem.SNOMED, "38341003",  "Hypertensive disorder")
        hyperlipid  = _concept(CodeSystem.SNOMED, "55822004",  "Hyperlipidemia")
        obesity     = _concept(CodeSystem.SNOMED, "414916001", "Obesity")
        gerd        = _concept(CodeSystem.SNOMED, "235595009", "Gastroesophageal reflux disease")

        # Medications (RxNorm)
        metformin  = _concept(CodeSystem.RXNORM, "861007", "Metformin 500 MG Oral Tablet")
        lisinopril = _concept(CodeSystem.RXNORM, "314076", "Lisinopril 10 MG Oral Tablet")
        atorvasta  = _concept(CodeSystem.RXNORM, "617310", "Atorvastatin 40 MG Oral Tablet")
        omeprazole = _concept(CodeSystem.RXNORM, "197321", "Omeprazole 20 MG Oral Capsule")
        aspirin    = _concept(CodeSystem.RXNORM, "243670", "Aspirin 81 MG Oral Tablet")

        self.stdout.write("  Concepts ready")

        # 4. Seed Observations
        random.seed(42)  # reproducible values
        obs_batch: list[Observation] = []

        # 4a. Monthly vitals over 24 months
        for month in range(24):
            days_ago = 30 * (24 - month)
            bp_group = uuid.uuid4()
            effective = _dt(days_ago, hour=random.choice([8, 9, 10, 14, 15]))

            # Systolic BP (trending down: 155 -> 132)
            sys_val = round(155 - month * 0.9 + random.uniform(-6, 6), 1)
            obs_batch.append(Observation(
                patient=user,
                status=ObservationStatus.FINAL,
                category=ObservationCategory.VITAL_SIGNS,
                code=bp_sys,
                value_quantity=Decimal(str(sys_val)),
                value_unit="mmHg",
                reference_low=Decimal("90"),
                reference_high=Decimal("140"),
                reference_text="90-140 mmHg",
                component_group_id=bp_group,
                component_code="systolic",
                effective_datetime=effective,
                recorded_datetime=effective,
                performer="Dr. Meredith Hayes, MD",
            ))

            # Diastolic BP (trending down: 95 -> 83)
            dia_val = round(95 - month * 0.5 + random.uniform(-4, 4), 1)
            obs_batch.append(Observation(
                patient=user,
                status=ObservationStatus.FINAL,
                category=ObservationCategory.VITAL_SIGNS,
                code=bp_dia,
                value_quantity=Decimal(str(dia_val)),
                value_unit="mmHg",
                reference_low=Decimal("60"),
                reference_high=Decimal("90"),
                reference_text="60-90 mmHg",
                component_group_id=bp_group,
                component_code="diastolic",
                effective_datetime=effective,
                recorded_datetime=effective,
                performer="Dr. Meredith Hayes, MD",
            ))

            # Heart rate
            hr_val = round(random.uniform(62, 84), 0)
            obs_batch.append(Observation(
                patient=user,
                status=ObservationStatus.FINAL,
                category=ObservationCategory.VITAL_SIGNS,
                code=hr,
                value_quantity=Decimal(str(hr_val)),
                value_unit="bpm",
                reference_low=Decimal("60"),
                reference_high=Decimal("100"),
                reference_text="60-100 bpm",
                effective_datetime=effective,
                recorded_datetime=effective,
                performer="Dr. Meredith Hayes, MD",
            ))

            # Weight kg (slow loss: 98 -> 91 kg)
            wt_val = round(98 - month * 0.28 + random.uniform(-0.5, 0.5), 1)
            obs_batch.append(Observation(
                patient=user,
                status=ObservationStatus.FINAL,
                category=ObservationCategory.VITAL_SIGNS,
                code=weight,
                value_quantity=Decimal(str(wt_val)),
                value_unit="kg",
                effective_datetime=effective,
                recorded_datetime=effective,
                performer="Dr. Meredith Hayes, MD",
            ))

        # Height (once)
        obs_batch.append(Observation(
            patient=user,
            status=ObservationStatus.FINAL,
            category=ObservationCategory.VITAL_SIGNS,
            code=height,
            value_quantity=Decimal("178.0"),
            value_unit="cm",
            effective_datetime=_dt(730),
            recorded_datetime=_dt(730),
            performer="Dr. Meredith Hayes, MD",
        ))

        # BMI quarterly
        for q in range(8):
            days_ago = 90 * (8 - q)
            wt = 98 - q * 0.84
            bmi_val = round(wt / (1.78 ** 2), 1)
            obs_batch.append(Observation(
                patient=user,
                status=ObservationStatus.FINAL,
                category=ObservationCategory.VITAL_SIGNS,
                code=bmi,
                value_quantity=Decimal(str(bmi_val)),
                value_unit="kg/m2",
                reference_low=Decimal("18.5"),
                reference_high=Decimal("24.9"),
                reference_text="18.5-24.9 kg/m2",
                effective_datetime=_dt(days_ago),
                recorded_datetime=_dt(days_ago),
                performer="Dr. Meredith Hayes, MD",
            ))

        # 4b. Quarterly lab panels over 24 months
        for q in range(8):
            days_ago = 90 * (8 - q)
            lab_dt = _dt(days_ago, hour=7)

            # Glucose fasting (trending down: 195 -> 118)
            gluc_val = round(195 - q * 9 + random.uniform(-8, 8), 1)
            obs_batch.append(Observation(
                patient=user, status=ObservationStatus.FINAL,
                category=ObservationCategory.LABORATORY, code=glucose,
                value_quantity=Decimal(str(gluc_val)), value_unit="mg/dL",
                reference_low=Decimal("70"), reference_high=Decimal("99"),
                reference_text="70-99 mg/dL fasting",
                effective_datetime=lab_dt, recorded_datetime=lab_dt,
                performer="City Lab Services",
            ))

            # HbA1c (trending down: 9.2 -> 6.8)
            hba_val = round(9.2 - q * 0.3 + random.uniform(-0.15, 0.15), 1)
            obs_batch.append(Observation(
                patient=user, status=ObservationStatus.FINAL,
                category=ObservationCategory.LABORATORY, code=hba1c,
                value_quantity=Decimal(str(hba_val)), value_unit="%",
                reference_low=Decimal("4.0"), reference_high=Decimal("5.6"),
                reference_text="<5.7% normal; 5.7-6.4% pre-diabetes; >=6.5% diabetes",
                effective_datetime=lab_dt, recorded_datetime=lab_dt,
                performer="City Lab Services",
            ))

            # Total cholesterol (trending down: 248 -> 188)
            chol_val = round(248 - q * 7.5 + random.uniform(-5, 5), 0)
            obs_batch.append(Observation(
                patient=user, status=ObservationStatus.FINAL,
                category=ObservationCategory.LABORATORY, code=chol,
                value_quantity=Decimal(str(chol_val)), value_unit="mg/dL",
                reference_high=Decimal("200"), reference_text="<200 mg/dL desirable",
                effective_datetime=lab_dt, recorded_datetime=lab_dt,
                performer="City Lab Services",
            ))

            # HDL (trending up: 38 -> 44)
            hdl_val = round(38 + q * 0.8 + random.uniform(-2, 2), 0)
            obs_batch.append(Observation(
                patient=user, status=ObservationStatus.FINAL,
                category=ObservationCategory.LABORATORY, code=hdl,
                value_quantity=Decimal(str(hdl_val)), value_unit="mg/dL",
                reference_low=Decimal("40"), reference_text=">40 mg/dL",
                effective_datetime=lab_dt, recorded_datetime=lab_dt,
                performer="City Lab Services",
            ))

            # LDL (trending down: 162 -> 105)
            ldl_val = round(162 - q * 7.1 + random.uniform(-5, 5), 0)
            obs_batch.append(Observation(
                patient=user, status=ObservationStatus.FINAL,
                category=ObservationCategory.LABORATORY, code=ldl,
                value_quantity=Decimal(str(ldl_val)), value_unit="mg/dL",
                reference_high=Decimal("100"), reference_text="<100 mg/dL optimal",
                effective_datetime=lab_dt, recorded_datetime=lab_dt,
                performer="City Lab Services",
            ))

            # Triglycerides (trending down: 290 -> 165)
            trig_val = round(290 - q * 15.6 + random.uniform(-10, 10), 0)
            obs_batch.append(Observation(
                patient=user, status=ObservationStatus.FINAL,
                category=ObservationCategory.LABORATORY, code=trig,
                value_quantity=Decimal(str(trig_val)), value_unit="mg/dL",
                reference_high=Decimal("150"), reference_text="<150 mg/dL",
                effective_datetime=lab_dt, recorded_datetime=lab_dt,
                performer="City Lab Services",
            ))

            # Creatinine
            creat_val = round(1.1 + random.uniform(-0.1, 0.2), 2)
            obs_batch.append(Observation(
                patient=user, status=ObservationStatus.FINAL,
                category=ObservationCategory.LABORATORY, code=creat,
                value_quantity=Decimal(str(creat_val)), value_unit="mg/dL",
                reference_low=Decimal("0.7"), reference_high=Decimal("1.3"),
                reference_text="0.7-1.3 mg/dL",
                effective_datetime=lab_dt, recorded_datetime=lab_dt,
                performer="City Lab Services",
            ))

            # eGFR
            egfr_val = round(72 - q * 1.2 + random.uniform(-3, 3), 0)
            obs_batch.append(Observation(
                patient=user, status=ObservationStatus.FINAL,
                category=ObservationCategory.LABORATORY, code=egfr,
                value_quantity=Decimal(str(egfr_val)), value_unit="mL/min/1.73m2",
                reference_low=Decimal("60"), reference_text=">60 mL/min/1.73m2",
                effective_datetime=lab_dt, recorded_datetime=lab_dt,
                performer="City Lab Services",
            ))

            # TSH (bi-annually — only even quarters)
            if q % 2 == 0:
                tsh_val = round(random.uniform(1.2, 2.8), 2)
                obs_batch.append(Observation(
                    patient=user, status=ObservationStatus.FINAL,
                    category=ObservationCategory.LABORATORY, code=tsh,
                    value_quantity=Decimal(str(tsh_val)), value_unit="mIU/L",
                    reference_low=Decimal("0.4"), reference_high=Decimal("4.0"),
                    reference_text="0.4-4.0 mIU/L",
                    effective_datetime=lab_dt, recorded_datetime=lab_dt,
                    performer="City Lab Services",
                ))

        Observation.objects.bulk_create(obs_batch)
        self.stdout.write(f"  Created {len(obs_batch)} observations")

        # 5. Seed Conditions
        conditions_data = [
            dict(
                code=t2dm_snomed,
                clinical_status=ConditionClinicalStatus.ACTIVE,
                verification_status=ConditionVerificationStatus.CONFIRMED,
                severity="moderate",
                onset_datetime=_dt(730),
                asserter="Dr. Meredith Hayes, MD",
                note="Patient diagnosed with T2DM. HbA1c improving on Metformin.",
            ),
            dict(
                code=htn_snomed,
                clinical_status=ConditionClinicalStatus.ACTIVE,
                verification_status=ConditionVerificationStatus.CONFIRMED,
                severity="mild",
                onset_datetime=_dt(600),
                asserter="Dr. Meredith Hayes, MD",
                note="Essential hypertension, responding to Lisinopril.",
            ),
            dict(
                code=hyperlipid,
                clinical_status=ConditionClinicalStatus.ACTIVE,
                verification_status=ConditionVerificationStatus.CONFIRMED,
                severity="moderate",
                onset_datetime=_dt(700),
                asserter="Dr. Meredith Hayes, MD",
                note="Mixed dyslipidemia; LDL improving on statin therapy.",
            ),
            dict(
                code=obesity,
                clinical_status=ConditionClinicalStatus.ACTIVE,
                verification_status=ConditionVerificationStatus.CONFIRMED,
                severity="moderate",
                onset_datetime=_dt(1200),
                asserter="Dr. Meredith Hayes, MD",
                note="BMI 30.9. Patient engaged in dietary and exercise plan.",
            ),
            dict(
                code=gerd,
                clinical_status=ConditionClinicalStatus.ACTIVE,
                verification_status=ConditionVerificationStatus.CONFIRMED,
                severity="mild",
                onset_datetime=_dt(400),
                asserter="Dr. Meredith Hayes, MD",
                note="Managed with Omeprazole; symptoms controlled.",
            ),
        ]

        for d in conditions_data:
            Condition.objects.get_or_create(patient=user, code=d["code"], defaults=d)
        self.stdout.write(f"  Upserted {len(conditions_data)} conditions")

        # 6. Seed MedicationStatements
        meds_data = [
            dict(
                medication_code=metformin,
                medication_text="Metformin 500 mg",
                status=MedicationStatus.ACTIVE,
                dose_value=Decimal("500"),
                dose_unit="mg",
                frequency_text="Twice daily with meals",
                route="oral",
                period_start=_dt(720),
                adherence_status=AdherenceStatus.TAKING,
                adherence_percentage=92,
                prescriber="Dr. Meredith Hayes, MD",
                note="Titrated to 1000mg/day over 3 months. Well tolerated.",
            ),
            dict(
                medication_code=lisinopril,
                medication_text="Lisinopril 10 mg",
                status=MedicationStatus.ACTIVE,
                dose_value=Decimal("10"),
                dose_unit="mg",
                frequency_text="Once daily in the morning",
                route="oral",
                period_start=_dt(590),
                adherence_status=AdherenceStatus.TAKING,
                adherence_percentage=88,
                prescriber="Dr. Meredith Hayes, MD",
                note="BP controlled. Monitor potassium and creatinine.",
            ),
            dict(
                medication_code=atorvasta,
                medication_text="Atorvastatin 40 mg",
                status=MedicationStatus.ACTIVE,
                dose_value=Decimal("40"),
                dose_unit="mg",
                frequency_text="Once daily at bedtime",
                route="oral",
                period_start=_dt(680),
                adherence_status=AdherenceStatus.TAKING,
                adherence_percentage=95,
                prescriber="Dr. Meredith Hayes, MD",
                note="LDL-C target <100 mg/dL. Monitoring LFTs annually.",
            ),
            dict(
                medication_code=omeprazole,
                medication_text="Omeprazole 20 mg",
                status=MedicationStatus.ACTIVE,
                dose_value=Decimal("20"),
                dose_unit="mg",
                frequency_text="Once daily before breakfast",
                route="oral",
                period_start=_dt(395),
                adherence_status=AdherenceStatus.PARTIAL,
                adherence_percentage=75,
                prescriber="Dr. Meredith Hayes, MD",
                note="Patient sometimes skips on weekends.",
            ),
            dict(
                medication_code=aspirin,
                medication_text="Aspirin 81 mg",
                status=MedicationStatus.ACTIVE,
                dose_value=Decimal("81"),
                dose_unit="mg",
                frequency_text="Once daily with food",
                route="oral",
                period_start=_dt(700),
                adherence_status=AdherenceStatus.TAKING,
                adherence_percentage=98,
                prescriber="Dr. Meredith Hayes, MD",
                note="Cardiovascular primary prevention per AHA guidelines.",
            ),
        ]

        for d in meds_data:
            MedicationStatement.objects.get_or_create(
                patient=user, medication_code=d["medication_code"], defaults=d
            )
        self.stdout.write(f"  Upserted {len(meds_data)} medications")

        # 7. Summary
        self.stdout.write(self.style.SUCCESS("\nSample data seeding complete!"))
        self.stdout.write(f"  Username : {username}")
        self.stdout.write(f"  Password : {password}")
        self.stdout.write(f"  Patient  : Alex Rivera (DOB 1978-04-15)")
        self.stdout.write(
            f"  Data     : {len(obs_batch)} observations | "
            f"{len(conditions_data)} conditions | "
            f"{len(meds_data)} medications"
        )
