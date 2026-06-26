"""
Django ORM models for the Patient-Centric Longitudinal Health Dashboard.

Structural alignment with HL7 FHIR R4 resources:
  - PatientUser + PatientProfile  →  Patient
  - Observation                   →  Observation
  - Condition                     →  Condition
  - MedicationStatement           →  MedicationStatement
  - AuditLog                      →  Provenance / AuditEvent (internal)

Longitudinal history is anchored on effective_datetime (clinical moment) and
recorded_datetime (when the fact entered the record), enabling accurate
timeline reconstruction across multi-year care episodes.
"""
from __future__ import annotations

import uuid
from typing import Optional

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from clinical.fields.encryption import EncryptedCharField, EncryptedTextField


# ---------------------------------------------------------------------------
# Enumerations (FHIR value-set aligned)
# ---------------------------------------------------------------------------

class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
    UNKNOWN = "unknown", "Unknown"


class ObservationCategory(models.TextChoices):
    VITAL_SIGNS = "vital-signs", "Vital Signs"
    LABORATORY = "laboratory", "Laboratory"
    SURVEY = "survey", "Survey"
    EXAM = "exam", "Exam"
    SOCIAL_HISTORY = "social-history", "Social History"


class ObservationStatus(models.TextChoices):
    REGISTERED = "registered", "Registered"
    PRELIMINARY = "preliminary", "Preliminary"
    FINAL = "final", "Final"
    AMENDED = "amended", "Amended"
    CORRECTED = "corrected", "Corrected"
    CANCELLED = "cancelled", "Cancelled"


class ConditionClinicalStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    RECURRENCE = "recurrence", "Recurrence"
    RELAPSE = "relapse", "Relapse"
    INACTIVE = "inactive", "Inactive"
    REMISSION = "remission", "Remission"
    RESOLVED = "resolved", "Resolved"


class ConditionVerificationStatus(models.TextChoices):
    UNCONFIRMED = "unconfirmed", "Unconfirmed"
    PROVISIONAL = "provisional", "Provisional"
    DIFFERENTIAL = "differential", "Differential"
    CONFIRMED = "confirmed", "Confirmed"
    REFUTED = "refuted", "Refuted"


class MedicationStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    STOPPED = "stopped", "Stopped"
    ON_HOLD = "on-hold", "On Hold"
    CANCELLED = "cancelled", "Cancelled"


class AdherenceStatus(models.TextChoices):
    TAKING = "taking", "Taking as prescribed"
    PARTIAL = "partial", "Taking partially"
    NOT_TAKING = "not-taking", "Not taking"
    UNKNOWN = "unknown", "Unknown"


class AuditAction(models.TextChoices):
    CREATE = "CREATE", "Create"
    READ = "READ", "Read"
    UPDATE = "UPDATE", "Update"
    DELETE = "DELETE", "Delete"
    EXPORT = "EXPORT", "Export"
    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Logout"
    ML_INFERENCE = "ML_INFERENCE", "ML Inference"


class UserRole(models.TextChoices):
    PATIENT = "patient", "Patient"
    CAREGIVER = "caregiver", "Caregiver"
    CLINICIAN = "clinician", "Clinician"
    ADMIN = "admin", "Administrator"


# ---------------------------------------------------------------------------
# FHIR-aligned coding helper (LOINC / SNOMED / RxNorm stored relationally)
# ---------------------------------------------------------------------------

class CodeSystem(models.TextChoices):
    LOINC = "http://loinc.org", "LOINC"
    SNOMED = "http://snomed.info/sct", "SNOMED CT"
    RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm", "RxNorm"
    ICD10 = "http://hl7.org/fhir/sid/icd-10-cm", "ICD-10-CM"


class CodedConcept(models.Model):
    """
    Reusable coded concept table mirroring FHIR CodeableConcept.coding[].
  Supports fast lookups and consistent display labels across resources.
    """

    system = models.CharField(max_length=128, choices=CodeSystem.choices, db_index=True)
    code = models.CharField(max_length=64, db_index=True)
    display = models.CharField(max_length=256)
    version = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        db_table = "clinical_coded_concept"
        constraints = [
            models.UniqueConstraint(
                fields=["system", "code", "version"],
                name="uq_coded_concept_system_code_version",
            ),
        ]
        indexes = [
            models.Index(fields=["system", "code"], name="idx_concept_system_code"),
        ]

    def __str__(self) -> str:
        return f"{self.display} ({self.code})"


# ---------------------------------------------------------------------------
# Patient (FHIR Patient + Django auth)
# ---------------------------------------------------------------------------

class PatientUser(AbstractUser):
    """
    Authenticated portal user. RBAC enforces patient_id == request.user.id
    for all clinical resource access in API layers.
    """

    role = models.CharField(
        max_length=16,
        choices=UserRole.choices,
        default=UserRole.PATIENT,
        db_index=True,
    )
    fhir_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        db_table = "clinical_patient_user"
        indexes = [
            models.Index(fields=["role"], name="idx_patient_user_role"),
        ]

    @property
    def is_patient(self) -> bool:
        return self.role == UserRole.PATIENT


class PatientProfile(models.Model):
    """
    FHIR Patient resource — demographic and contact PHI stored with
    field-level AES-256 encryption for identifiers and free-text notes.
    """

    user = models.OneToOneField(
        PatientUser,
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
    )
    fhir_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # FHIR Patient.identifier (encrypted MRN / external IDs)
    medical_record_number = EncryptedCharField(max_length=128, blank=True, default="")
    identifier_system = models.CharField(max_length=128, blank=True, default="")

    # FHIR Patient.name (encrypted for HIPAA at-rest posture)
    given_name = EncryptedCharField(max_length=128)
    family_name = EncryptedCharField(max_length=128)
    preferred_name = EncryptedCharField(max_length=128, blank=True, default="")

    # FHIR Patient.birthDate / gender
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=16, choices=Gender.choices, default=Gender.UNKNOWN)

    # FHIR Patient.telecom / address (encrypted contact details)
    phone = EncryptedCharField(max_length=32, blank=True, default="")
    email_contact = EncryptedCharField(max_length=256, blank=True, default="")
    address_line = EncryptedCharField(max_length=256, blank=True, default="")
    city = EncryptedCharField(max_length=128, blank=True, default="")
    state = EncryptedCharField(max_length=64, blank=True, default="")
    postal_code = EncryptedCharField(max_length=16, blank=True, default="")
    country = models.CharField(max_length=2, default="US")

    # Longitudinal care context
    primary_care_provider = models.CharField(max_length=256, blank=True, default="")
    care_team_notes = EncryptedTextField(blank=True, default="")

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinical_patient_profile"
        indexes = [
            models.Index(fields=["active"], name="idx_patient_profile_active"),
            models.Index(fields=["birth_date"], name="idx_patient_profile_dob"),
        ]

    def __str__(self) -> str:
        return f"Patient<{self.user_id}>"

    @property
    def patient_id(self) -> int:
        """Canonical patient identifier used in RBAC checks."""
        return self.user_id


# ---------------------------------------------------------------------------
# Observation (FHIR Observation — vitals, labs, surveys)
# ---------------------------------------------------------------------------

class Observation(models.Model):
    """
    FHIR Observation with quantitative value, reference range, and dual
    timestamps for longitudinal timeline aggregation.

    effective_datetime  → when the measurement clinically occurred
    recorded_datetime   → when this version entered the health record
    """

    patient = models.ForeignKey(
        PatientUser,
        on_delete=models.CASCADE,
        related_name="observations",
        db_index=True,
    )
    fhir_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    status = models.CharField(
        max_length=16,
        choices=ObservationStatus.choices,
        default=ObservationStatus.FINAL,
        db_index=True,
    )
    category = models.CharField(
        max_length=32,
        choices=ObservationCategory.choices,
        default=ObservationCategory.LABORATORY,
        db_index=True,
    )
    code = models.ForeignKey(
        CodedConcept,
        on_delete=models.PROTECT,
        related_name="observations",
    )

    # FHIR Observation.value[x] — numeric labs/vitals
    value_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
    )
    value_unit = models.CharField(max_length=32, blank=True, default="")
    value_string = models.CharField(max_length=256, blank=True, default="")

    # FHIR Observation.referenceRange
    reference_low = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Lower bound of normal reference range.",
    )
    reference_high = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Upper bound of normal reference range.",
    )
    reference_text = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Human-readable range, e.g. '70-99 mg/dL fasting'.",
    )

    # Component support for BP (systolic/diastolic pair stored as sibling rows
    # sharing component_group_id, or as separate coded observations)
    component_group_id = models.UUIDField(null=True, blank=True, db_index=True)
    component_code = models.CharField(max_length=64, blank=True, default="")

    # Longitudinal anchors
    effective_datetime = models.DateTimeField(db_index=True)
    recorded_datetime = models.DateTimeField(default=timezone.now, db_index=True)
    issued_datetime = models.DateTimeField(null=True, blank=True)

    # Encrypted clinician interpretation / patient-facing lab notes
    interpretation = models.CharField(max_length=64, blank=True, default="")
    note = EncryptedTextField(blank=True, default="")

    performer = models.CharField(max_length=256, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinical_observation"
        ordering = ["effective_datetime", "recorded_datetime"]
        indexes = [
            models.Index(
                fields=["patient", "effective_datetime"],
                name="idx_obs_patient_effective",
            ),
            models.Index(
                fields=["patient", "code", "effective_datetime"],
                name="idx_obs_patient_code_effective",
            ),
            models.Index(
                fields=["patient", "category", "effective_datetime"],
                name="idx_obs_patient_cat_effective",
            ),
            models.Index(fields=["component_group_id"], name="idx_obs_component_grp"),
        ]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(value_quantity__isnull=False)
                    | ~models.Q(value_string="")
                ),
                name="chk_observation_has_value",
            ),
        ]

    def __str__(self) -> str:
        return f"Observation<{self.code_id}> patient={self.patient_id} @ {self.effective_datetime}"

    @property
    def is_in_reference_range(self) -> Optional[bool]:
        if self.value_quantity is None:
            return None
        val = float(self.value_quantity)
        if self.reference_low is not None and val < float(self.reference_low):
            return False
        if self.reference_high is not None and val > float(self.reference_high):
            return False
        if self.reference_low is not None or self.reference_high is not None:
            return True
        return None


# ---------------------------------------------------------------------------
# Condition (FHIR Condition — diagnoses / problems)
# ---------------------------------------------------------------------------

class Condition(models.Model):
    """
    FHIR Condition representing diagnoses with onset/abatement periods
    for longitudinal problem-list tracking.
    """

    patient = models.ForeignKey(
        PatientUser,
        on_delete=models.CASCADE,
        related_name="conditions",
        db_index=True,
    )
    fhir_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    clinical_status = models.CharField(
        max_length=16,
        choices=ConditionClinicalStatus.choices,
        default=ConditionClinicalStatus.ACTIVE,
        db_index=True,
    )
    verification_status = models.CharField(
        max_length=16,
        choices=ConditionVerificationStatus.choices,
        default=ConditionVerificationStatus.CONFIRMED,
    )
    severity = models.CharField(max_length=32, blank=True, default="")
    code = models.ForeignKey(
        CodedConcept,
        on_delete=models.PROTECT,
        related_name="conditions",
    )

    # FHIR Condition.onset[x] / abatement[x]
    onset_datetime = models.DateTimeField(null=True, blank=True, db_index=True)
    abatement_datetime = models.DateTimeField(null=True, blank=True, db_index=True)

    # Longitudinal record versioning
    recorded_datetime = models.DateTimeField(default=timezone.now, db_index=True)
    effective_datetime = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Primary timeline sort key; defaults to onset_datetime in save().",
    )

    note = EncryptedTextField(blank=True, default="")
    asserter = models.CharField(max_length=256, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinical_condition"
        ordering = ["effective_datetime", "recorded_datetime"]
        indexes = [
            models.Index(
                fields=["patient", "clinical_status", "effective_datetime"],
                name="idx_cond_patient_status_eff",
            ),
            models.Index(
                fields=["patient", "code"],
                name="idx_cond_patient_code",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.effective_datetime:
            self.effective_datetime = self.onset_datetime or self.recorded_datetime
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Condition<{self.code_id}> patient={self.patient_id}"


# ---------------------------------------------------------------------------
# MedicationStatement (FHIR MedicationStatement + adherence)
# ---------------------------------------------------------------------------

class MedicationStatement(models.Model):
    """
    FHIR MedicationStatement with dosage instructions and adherence
    tracking for longitudinal medication history.
    """

    patient = models.ForeignKey(
        PatientUser,
        on_delete=models.CASCADE,
        related_name="medication_statements",
        db_index=True,
    )
    fhir_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    status = models.CharField(
        max_length=16,
        choices=MedicationStatus.choices,
        default=MedicationStatus.ACTIVE,
        db_index=True,
    )
    medication_code = models.ForeignKey(
        CodedConcept,
        on_delete=models.PROTECT,
        related_name="medications",
    )
    medication_text = models.CharField(max_length=256, blank=True, default="")

    # FHIR Dosage
    dose_value = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    dose_unit = models.CharField(max_length=32, blank=True, default="")
    frequency_text = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="e.g. 'Once daily with breakfast'.",
    )
    route = models.CharField(max_length=64, blank=True, default="oral")

    # FHIR effectivePeriod
    period_start = models.DateTimeField(db_index=True)
    period_end = models.DateTimeField(null=True, blank=True, db_index=True)

    # Longitudinal anchors
    effective_datetime = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timeline sort key; defaults to period_start.",
    )
    recorded_datetime = models.DateTimeField(default=timezone.now, db_index=True)

    # Adherence tracking (patient-reported or derived)
    adherence_status = models.CharField(
        max_length=16,
        choices=AdherenceStatus.choices,
        default=AdherenceStatus.UNKNOWN,
        db_index=True,
    )
    adherence_percentage = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Self-reported or calculated adherence 0-100%.",
    )
    adherence_recorded_at = models.DateTimeField(null=True, blank=True)

    note = EncryptedTextField(blank=True, default="")
    prescriber = models.CharField(max_length=256, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "clinical_medication_statement"
        ordering = ["effective_datetime", "recorded_datetime"]
        indexes = [
            models.Index(
                fields=["patient", "status", "effective_datetime"],
                name="idx_meds_patient_status_eff",
            ),
            models.Index(
                fields=["patient", "period_start", "period_end"],
                name="idx_meds_patient_period",
            ),
            models.Index(
                fields=["patient", "adherence_status"],
                name="idx_meds_patient_adherence",
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.effective_datetime:
            self.effective_datetime = self.period_start
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Medication<{self.medication_code_id}> patient={self.patient_id}"

    @property
    def is_active(self) -> bool:
        now = timezone.now()
        if self.status != MedicationStatus.ACTIVE:
            return False
        if self.period_end and self.period_end < now:
            return False
        return self.period_start <= now


# ---------------------------------------------------------------------------
# AuditLog (immutable access trail)
# ---------------------------------------------------------------------------

class AuditLog(models.Model):
    """
    Immutable audit trail for every PHI read/write and ML inference.
    Mirrors FHIR Provenance / IHE ATNA audit semantics at application layer.
    """

    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    user = models.ForeignKey(
        PatientUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
    )
    patient = models.ForeignKey(
        PatientUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_audit_entries",
        help_text="Subject patient whose PHI was accessed.",
    )

    action = models.CharField(max_length=16, choices=AuditAction.choices, db_index=True)
    resource_type = models.CharField(max_length=64, db_index=True)
    resource_id = models.CharField(max_length=64, blank=True, default="")

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True, default="")
    request_path = models.CharField(max_length=512, blank=True, default="")
    http_method = models.CharField(max_length=8, blank=True, default="")
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "clinical_audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["patient", "timestamp"], name="idx_audit_patient_ts"),
            models.Index(fields=["user", "timestamp"], name="idx_audit_user_ts"),
            models.Index(
                fields=["resource_type", "resource_id"],
                name="idx_audit_resource",
            ),
            models.Index(fields=["action", "timestamp"], name="idx_audit_action_ts"),
        ]

    def __str__(self) -> str:
        return f"AuditLog<{self.action} {self.resource_type}/{self.resource_id}>"


# ---------------------------------------------------------------------------
# ObservationAttachment (FHIR DocumentReference — camera / file uploads)
# ---------------------------------------------------------------------------

def patient_upload_path(instance: "ObservationAttachment", filename: str) -> str:
    """Store uploads in patient-scoped paths for RBAC isolation."""
    return f"patient_{instance.patient_id}/observations/{filename}"


class CaptureSource(models.TextChoices):
    CAMERA = "camera", "Camera"
    FILE = "file", "File upload"


class ObservationAttachment(models.Model):
    """
    Image captured from the patient portal camera or file picker, optionally
    linked to a numeric Observation created in the same submission.
    """

    patient = models.ForeignKey(
        PatientUser,
        on_delete=models.CASCADE,
        related_name="observation_attachments",
        db_index=True,
    )
    observation = models.ForeignKey(
        Observation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments",
    )
    fhir_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    image = models.ImageField(upload_to=patient_upload_path)
    capture_source = models.CharField(
        max_length=16,
        choices=CaptureSource.choices,
        default=CaptureSource.CAMERA,
    )
    original_filename = models.CharField(max_length=256, blank=True, default="")
    mime_type = models.CharField(max_length=64, blank=True, default="image/jpeg")
    file_size_bytes = models.PositiveIntegerField(default=0)

    caption = EncryptedCharField(max_length=256, blank=True, default="")
    uploaded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "clinical_observation_attachment"
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["patient", "uploaded_at"], name="idx_attach_patient_ts"),
        ]

    def __str__(self) -> str:
        return f"Attachment<{self.pk}> patient={self.patient_id}"
