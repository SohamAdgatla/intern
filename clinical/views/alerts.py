"""Smart Alerts API."""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from clinical.models import AuditAction, PatientUser, UserRole
from clinical.permissions import PatientOnlyPermission
from clinical.serializers.alerts import SmartAlertsResponseSerializer
from clinical.services.audit import log_audit_event
from clinical.services.smart_alerts import SmartAlertEngine


class SmartAlertsView(APIView):
    """GET /api/alerts/ — longitudinal pattern alerts in plain language."""

    permission_classes = [PatientOnlyPermission]

    def get(self, request):
        user: PatientUser = request.user

        if user.role == UserRole.PATIENT:
            if request.query_params.get("patient_id") not in (None, "", str(user.id)):
                return Response(
                    {"detail": "You may only access your own alerts."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            patient = user
        else:
            patient = user

        payload = SmartAlertEngine(patient).evaluate()
        serializer = SmartAlertsResponseSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        log_audit_event(
            request=request,
            action=AuditAction.READ,
            resource_type="SmartAlerts",
            resource_id=str(patient.id),
            patient_id=patient.id,
            status_code=status.HTTP_200_OK,
            metadata={"alert_count": payload["alert_count"]},
        )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
