"""
Role-Based Access Control for patient-owned PHI.

Core rule: authenticated patients may only access resources where
patient_id == request.user.id unless they hold an explicit clinical role
with documented break-glass authorization (not implemented in patient portal).
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

from clinical.models import UserRole


class PatientSelfAccessPermission(BasePermission):
    message = "You may only access your own health records."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role in (UserRole.CLINICIAN, UserRole.ADMIN):
            return True

        patient_id = getattr(obj, "patient_id", None)
        if patient_id is None and hasattr(obj, "patient"):
            patient_id = obj.patient_id
        if patient_id is None and hasattr(obj, "user_id"):
            patient_id = obj.user_id
        if patient_id is None:
            patient_id = getattr(obj, "pk", None)

        return patient_id == user.id


class PatientOnlyPermission(BasePermission):
    """Strict portal permission: user can only ever access self."""

    message = "Access denied. Patient identity mismatch."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role != UserRole.PATIENT:
            return request.user.role in (UserRole.CLINICIAN, UserRole.ADMIN)
        return True

    @staticmethod
    def resolve_patient_id(request, view) -> int:
        """Return the patient ID the request is authorized to access."""
        user = request.user
        if user.role == UserRole.PATIENT:
            return user.id
        return int(view.kwargs.get("patient_id", user.id))
