"""
Analytics API views — chronic disease risk assessment with RBAC + audit.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from clinical.models import AuditAction, PatientUser
from clinical.permissions import PatientOnlyPermission
from clinical.serializers.analytics import RiskAssessmentSerializer
from clinical.services.audit import log_audit_event
from clinical.services.ml_engine import ChronicDiseaseRiskEngine


class RiskAssessmentView(APIView):
    """
    GET /api/analytics/risk-assessment/

    Executes the scikit-learn chronic disease risk pipeline for the
    authenticated patient. RBAC enforces patient_id == request.user.id.
    """

    permission_classes = [PatientOnlyPermission]

    def get(self, request):
        user: PatientUser = request.user

        if user.role == "patient" and user.id != user.pk:
            return Response(
                {"detail": "Patient identity mismatch."},
                status=status.HTTP_403_FORBIDDEN,
            )

        patient = user
        target_patient_id = user.id

        try:
            result = ChronicDiseaseRiskEngine.assess_patient(patient)
        except Exception as exc:
            log_audit_event(
                request=request,
                action=AuditAction.ML_INFERENCE,
                resource_type="RiskAssessment",
                resource_id=str(target_patient_id),
                patient_id=target_patient_id,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                metadata={"error": str(exc)},
            )
            return Response(
                {"detail": "Risk assessment temporarily unavailable."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        payload = result.to_api_payload()
        serializer = RiskAssessmentSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        log_audit_event(
            request=request,
            action=AuditAction.ML_INFERENCE,
            resource_type="RiskAssessment",
            resource_id=str(target_patient_id),
            patient_id=target_patient_id,
            status_code=status.HTTP_200_OK,
            metadata={
                "model_version": result.model_version,
                "risk_label": result.risk_label,
                "risk_probability": result.risk_probability,
            },
        )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
