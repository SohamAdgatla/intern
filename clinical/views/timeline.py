"""
Timeline Aggregator API — unified chronological health history.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from clinical.models import AuditAction, PatientUser, UserRole
from clinical.permissions import PatientOnlyPermission
from clinical.serializers.timeline import TimelineResponseSerializer
from clinical.services.audit import log_audit_event
from clinical.services.timeline_aggregator import (
    TimelineAggregator,
    parse_timeline_query_params,
)


class TimelineAggregatorView(APIView):
    """
    GET /api/timeline/

    Queries Observations, Conditions, and MedicationStatements for the
    authenticated patient, normalizes them into a uniform event envelope,
    and returns a single array sorted oldest → newest.

    Query parameters
    ----------------
    from              : ISO-8601 lower bound on effective_datetime
    to                : ISO-8601 upper bound on effective_datetime
    types             : Comma-separated filter: observation,condition,medication
    categories        : Observation categories (e.g. laboratory,vital-signs)
    include_cancelled : true/false — include cancelled observations
    limit             : Max events returned (1–500, default all)
    """

    permission_classes = [PatientOnlyPermission]

    def get(self, request):
        user: PatientUser = request.user

        if user.role == UserRole.PATIENT and user.id != user.pk:
            return Response(
                {"detail": "Patient identity mismatch."},
                status=status.HTTP_403_FORBIDDEN,
            )

        patient_id = user.id
        if user.role in (UserRole.CLINICIAN, UserRole.ADMIN):
            requested_patient = request.query_params.get("patient_id")
            if requested_patient:
                try:
                    patient_id = int(requested_patient)
                except (TypeError, ValueError):
                    return Response(
                        {"detail": "patient_id must be a valid integer."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            patient = PatientUser.objects.filter(pk=patient_id).first()
            if not patient:
                return Response(
                    {"detail": "Patient not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            patient = user
            if request.query_params.get("patient_id") not in (None, "", str(user.id)):
                return Response(
                    {"detail": "You may only access your own timeline."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        try:
            params = parse_timeline_query_params(request.query_params)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = TimelineAggregator(patient, params).aggregate()

        serializer = TimelineResponseSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        log_audit_event(
            request=request,
            action=AuditAction.READ,
            resource_type="Timeline",
            resource_id=str(patient.id),
            patient_id=patient.id,
            status_code=status.HTTP_200_OK,
            metadata={
                "total_events": payload["total_events"],
                "returned_events": payload["returned_events"],
                "filters": payload["filters"],
            },
        )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
