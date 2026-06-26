"""
Mandatory PHI access audit middleware.

Every API read/write under /api/ produces an immutable AuditLog row once the
response is finalized, capturing actor, action, resource hint, and status.
"""
from __future__ import annotations

from clinical.services.audit import log_audit_event, map_http_method_to_action


class AuditLoggingMiddleware:
    AUDITED_PREFIX = "/api/"
    EXEMPT_PATHS = {"/api/health/"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not request.path.startswith(self.AUDITED_PREFIX):
            return response
        if request.path in self.EXEMPT_PATHS:
            return response

        user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        resource_type = self._infer_resource_type(request.path)
        action = map_http_method_to_action(request.method)

        log_audit_event(
            request=request,
            action=action,
            resource_type=resource_type,
            resource_id=self._extract_resource_id(request.path),
            patient_id=user.id if user else None,
            status_code=response.status_code,
            metadata={
                "query_params": dict(request.GET),
                "content_type": request.content_type or "",
            },
        )
        return response

    @staticmethod
    def _infer_resource_type(path: str) -> str:
        segments = [s for s in path.strip("/").split("/") if s]
        if len(segments) >= 2:
            return segments[1]
        return "api"

    @staticmethod
    def _extract_resource_id(path: str) -> str:
        segments = [s for s in path.strip("/").split("/") if s]
        if len(segments) >= 3 and segments[-1].isdigit():
            return segments[-1]
        return ""
