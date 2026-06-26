"""
Patient self-entry service — creates Observations and optional camera attachments.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from clinical.constants.measurements import MEASUREMENT_TYPES
from clinical.models import (
    CaptureSource,
    CodeSystem,
    CodedConcept,
    Observation,
    ObservationAttachment,
    ObservationCategory,
    PatientUser,
)


def get_or_create_loinc_concept(loinc_code: str) -> CodedConcept:
    meta = next((m for m in MEASUREMENT_TYPES if m["loinc_code"] == loinc_code), None)
    display = meta["display"] if meta else loinc_code
    concept, _ = CodedConcept.objects.get_or_create(
        system=CodeSystem.LOINC,
        code=loinc_code,
        version="",
        defaults={"display": display},
    )
    return concept


def resolve_measurement_meta(loinc_code: str) -> Dict[str, Any]:
    meta = next((m for m in MEASUREMENT_TYPES if m["loinc_code"] == loinc_code), None)
    if not meta:
        raise ValueError(f"Unsupported measurement type: {loinc_code}")
    return meta


def validate_image_upload(upload: UploadedFile) -> None:
    if upload.size > settings.MAX_UPLOAD_IMAGE_BYTES:
        raise ValueError("Image must be 5 MB or smaller.")
    content_type = getattr(upload, "content_type", "") or ""
    if content_type and content_type not in settings.ALLOWED_UPLOAD_MIME_TYPES:
        raise ValueError("Only JPEG, PNG, or WebP images are allowed.")


@transaction.atomic
def submit_patient_observation(
    patient: PatientUser,
    *,
    loinc_code: str,
    value_quantity: Optional[float] = None,
    value_unit: str = "",
    note: str = "",
    effective_datetime: Optional[str] = None,
    image: Optional[UploadedFile] = None,
    capture_source: str = CaptureSource.CAMERA,
    caption: str = "",
) -> Tuple[Optional[Observation], Optional[ObservationAttachment]]:
    """
    Create an Observation and optionally attach a camera-captured image.
    At least one of value_quantity or image must be provided.
    """
    if value_quantity is None and image is None:
        raise ValueError("Enter a measurement value or capture an image.")

    meta = resolve_measurement_meta(loinc_code)
    concept = get_or_create_loinc_concept(loinc_code)

    eff_dt = timezone.now()
    if effective_datetime:
        parsed = parse_datetime(effective_datetime)
        if parsed:
            eff_dt = parsed if timezone.is_aware(parsed) else timezone.make_aware(parsed)

    observation: Optional[Observation] = None
    attachment: Optional[ObservationAttachment] = None

    if value_quantity is not None:
        try:
            qty = Decimal(str(value_quantity))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Invalid numeric value.") from exc

        unit = value_unit or meta.get("unit", "")
        observation = Observation.objects.create(
            patient=patient,
            code=concept,
            category=meta["category"],
            value_quantity=qty,
            value_unit=unit,
            reference_low=meta.get("reference_low"),
            reference_high=meta.get("reference_high"),
            reference_text=(
                f"{meta['reference_low']}–{meta['reference_high']} {unit}".strip()
                if meta.get("reference_low") is not None
                else ""
            ),
            effective_datetime=eff_dt,
            note=note or "",
            performer="Patient self-entry",
        )

    if image is not None:
        validate_image_upload(image)
        attachment = ObservationAttachment.objects.create(
            patient=patient,
            observation=observation,
            image=image,
            capture_source=capture_source,
            original_filename=getattr(image, "name", "capture.jpg"),
            mime_type=getattr(image, "content_type", "image/jpeg") or "image/jpeg",
            file_size_bytes=image.size,
            caption=caption or note or meta["display"],
        )

    return observation, attachment


def observation_to_dict(obs: Observation) -> Dict[str, Any]:
    return {
        "id": obs.pk,
        "fhir_id": str(obs.fhir_id),
        "loinc_code": obs.code.code,
        "display": obs.code.display,
        "value_quantity": float(obs.value_quantity) if obs.value_quantity is not None else None,
        "value_unit": obs.value_unit,
        "effective_datetime": obs.effective_datetime.isoformat(),
        "in_reference_range": obs.is_in_reference_range,
    }


def attachment_to_dict(att: ObservationAttachment, request=None) -> Dict[str, Any]:
    image_url = att.image.url if att.image else None
    if request and image_url:
        image_url = request.build_absolute_uri(image_url)
    return {
        "id": att.pk,
        "fhir_id": str(att.fhir_id),
        "image_url": image_url,
        "capture_source": att.capture_source,
        "caption": att.caption,
        "uploaded_at": att.uploaded_at.isoformat(),
        "observation_id": att.observation_id,
    }
