"""
Health Story Mode API — empathetic plain-language summaries from longitudinal trends.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from clinical.models import AuditAction, PatientUser, UserRole
from clinical.permissions import PatientOnlyPermission
from clinical.serializers.health_story import HealthStorySerializer
from clinical.services.audit import log_audit_event
from clinical.services.health_story import HealthStoryEngine


class HealthStoryView(APIView):
    """
    GET /api/health-story/

    Runs the rule-based HealthStoryEngine for the authenticated patient,
    translating numeric trends into warm, jargon-free narrative text.

    Query parameters
    ----------------
    lookback_months : How far back to analyze (6–60, default 24)
    """

    permission_classes = [PatientOnlyPermission]

    def get(self, request):
        user: PatientUser = request.user

        if user.role == UserRole.PATIENT and user.id != user.pk:
            return Response(
                {"detail": "Patient identity mismatch."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.role == UserRole.PATIENT:
            if request.query_params.get("patient_id") not in (None, "", str(user.id)):
                return Response(
                    {"detail": "You may only access your own health story."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            patient = user
        else:
            patient_id_raw = request.query_params.get("patient_id", user.id)
            try:
                patient_id = int(patient_id_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "patient_id must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            patient = PatientUser.objects.filter(pk=patient_id).first()
            if not patient:
                return Response({"detail": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

        lookback_months = 24
        lookback_raw = request.query_params.get("lookback_months", "")
        if lookback_raw:
            try:
                lookback_months = int(lookback_raw)
            except ValueError:
                return Response(
                    {"detail": "lookback_months must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if lookback_months < 6 or lookback_months > 60:
                return Response(
                    {"detail": "lookback_months must be between 6 and 60."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            result = HealthStoryEngine(patient, lookback_months=lookback_months).generate()
        except Exception as exc:
            log_audit_event(
                request=request,
                action=AuditAction.READ,
                resource_type="HealthStory",
                resource_id=str(patient.id),
                patient_id=patient.id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                metadata={"error": str(exc)},
            )
            return Response(
                {"detail": "Health story temporarily unavailable."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        payload = result.to_api_payload()
        serializer = HealthStorySerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        log_audit_event(
            request=request,
            action=AuditAction.READ,
            resource_type="HealthStory",
            resource_id=str(patient.id),
            patient_id=patient.id,
            status_code=status.HTTP_200_OK,
            metadata={
                "lookback_months": lookback_months,
                "highlight_count": len(payload["highlights"]),
                "headline": payload["headline"],
            },
        )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
