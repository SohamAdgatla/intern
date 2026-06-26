"""
Performance audit middleware — logs slow requests for capacity planning.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger("clinical.audit")

SLOW_REQUEST_THRESHOLD_MS = 750


class PerformanceAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if elapsed_ms >= SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                "slow_request path=%s method=%s duration_ms=%.1f status=%s",
                request.path,
                request.method,
                elapsed_ms,
                response.status_code,
            )
        response["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
        return response
