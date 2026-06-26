"""Patient self-entry API — manual vitals + camera image upload."""
from __future__ import annotations

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from clinical.models import AuditAction, PatientUser
from clinical.permissions import PatientOnlyPermission
from clinical.serializers.patient_input import (
    SubmitResponseSerializer,
    measurement_types_payload,
)
from clinical.services.audit import log_audit_event
from clinical.services.patient_input import (
    attachment_to_dict,
    observation_to_dict,
    submit_patient_observation,
)


class MeasurementTypesView(APIView):
    """GET /api/observations/measurement-types/"""

    permission_classes = [PatientOnlyPermission]

    def get(self, request):
        return Response({"measurement_types": measurement_types_payload()})


class ObservationSubmitView(APIView):
    """
    POST /api/observations/submit/

    Accepts multipart/form-data (with optional camera image) or JSON.
    Fields: loinc_code, value_quantity, value_unit, note, effective_datetime,
            caption, capture_source, image (file)
    """

    permission_classes = [PatientOnlyPermission]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        user: PatientUser = request.user
        data = request.data

        loinc_code = data.get("loinc_code", "")
        if not loinc_code:
            return Response(
                {"detail": "loinc_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        value_raw = data.get("value_quantity")
        value_quantity = None
        if value_raw not in (None, ""):
            try:
                value_quantity = float(value_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "value_quantity must be a number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        image = request.FILES.get("image")

        try:
            observation, attachment = submit_patient_observation(
                user,
                loinc_code=loinc_code,
                value_quantity=value_quantity,
                value_unit=data.get("value_unit", ""),
                note=data.get("note", ""),
                effective_datetime=data.get("effective_datetime"),
                image=image,
                capture_source=data.get("capture_source", "camera"),
                caption=data.get("caption", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            log_audit_event(
                request=request,
                action=AuditAction.CREATE,
                resource_type="Observation",
                patient_id=user.id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                metadata={"error": str(exc)},
            )
            return Response(
                {"detail": "Could not save your health entry."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        payload = {
            "message": "Your health entry was saved successfully.",
            "observation": observation_to_dict(observation) if observation else None,
            "attachment": attachment_to_dict(attachment, request) if attachment else None,
        }

        serializer = SubmitResponseSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        log_audit_event(
            request=request,
            action=AuditAction.CREATE,
            resource_type="Observation",
            resource_id=str(observation.pk if observation else attachment.pk),
            patient_id=user.id,
            status_code=status.HTTP_201_CREATED,
            metadata={
                "loinc_code": loinc_code,
                "has_image": attachment is not None,
            },
        )

        return Response(serializer.validated_data, status=status.HTTP_201_CREATED)
