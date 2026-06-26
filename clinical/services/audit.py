"""
Centralized audit logging for HIPAA-minded access tracking.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.http import HttpRequest

from clinical.models import AuditAction, AuditLog

audit_logger = logging.getLogger("clinical.audit")


def log_audit_event(
    *,
    request: Optional[HttpRequest],
    action: str,
    resource_type: str,
    resource_id: str = "",
    patient_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    status_code: Optional[int] = None,
) -> AuditLog:
    user = request.user if request and getattr(request, "user", None) and request.user.is_authenticated else None
    ip_address = _client_ip(request) if request else None
    user_agent = (request.META.get("HTTP_USER_AGENT", "")[:512] if request else "")

    entry = AuditLog.objects.create(
        user=user,
        patient_id=patient_id or (user.id if user else None),
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else "",
        ip_address=ip_address,
        user_agent=user_agent,
        request_path=request.path[:512] if request else "",
        http_method=request.method if request else "",
        status_code=status_code,
        metadata=metadata or {},
    )

    audit_logger.info(
        "audit user=%s action=%s resource=%s/%s patient=%s",
        user.id if user else "anonymous",
        action,
        resource_type,
        resource_id,
        patient_id,
    )
    return entry


def _client_ip(request: HttpRequest) -> Optional[str]:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def map_http_method_to_action(method: str) -> str:
    mapping = {
        "GET": AuditAction.READ,
        "HEAD": AuditAction.READ,
        "POST": AuditAction.CREATE,
        "PUT": AuditAction.UPDATE,
        "PATCH": AuditAction.UPDATE,
        "DELETE": AuditAction.DELETE,
    }
    return mapping.get(method.upper(), AuditAction.READ)
