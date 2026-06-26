"""
Timeline Aggregator — normalizes Observations, Conditions, and MedicationStatements
into a single chronological payload for the patient health story UI.

All events share a uniform envelope while preserving FHIR-aligned resource details
in a nested `details` object for frontend rendering flexibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Set

from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from clinical.models import (
    Condition,
    MedicationStatement,
    Observation,
    ObservationStatus,
    PatientUser,
)


TIMELINE_RESOURCE_TYPES = frozenset({"observation", "condition", "medication"})


@dataclass(frozen=True)
class TimelineQueryParams:
    """Validated filters for timeline aggregation."""

    from_datetime: Optional[datetime] = None
    to_datetime: Optional[datetime] = None
    resource_types: Optional[Set[str]] = None
    observation_categories: Optional[Set[str]] = None
    include_cancelled: bool = False
    limit: Optional[int] = None


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone=timezone.utc)
    return dt.isoformat()


def _decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
    return float(value) if value is not None else None


def _coding_dict(code_obj) -> Dict[str, str]:
    return {
        "system": code_obj.system,
        "code": code_obj.code,
        "display": code_obj.display,
        "version": code_obj.version or "",
    }


def _build_observation_summary(obs: Observation) -> str:
    label = obs.code.display
    if obs.value_quantity is not None:
        value_part = f"{obs.value_quantity:g}"
        if obs.value_unit:
            value_part = f"{value_part} {obs.value_unit}"
        range_hint = obs.reference_text
        if not range_hint and obs.reference_low is not None and obs.reference_high is not None:
            range_hint = f"{obs.reference_low:g}–{obs.reference_high:g}"
        in_range = obs.is_in_reference_range
        if in_range is True:
            return f"{label} measured at {value_part} (within expected range)"
        if in_range is False:
            return f"{label} measured at {value_part} (outside expected range — your care team can explain)"
        return f"{label} measured at {value_part}"
    if obs.value_string:
        return f"{label}: {obs.value_string}"
    return label


def _normalize_observation(obs: Observation) -> Dict[str, Any]:
    sort_dt = obs.effective_datetime
    return {
        "id": f"observation:{obs.pk}",
        "resource_type": "observation",
        "resource_id": obs.pk,
        "fhir_id": str(obs.fhir_id),
        "sort_datetime": _iso(sort_dt),
        "effective_datetime": _iso(obs.effective_datetime),
        "recorded_datetime": _iso(obs.recorded_datetime),
        "title": obs.code.display,
        "subtitle": (
            f"{obs.value_quantity:g} {obs.value_unit}".strip()
            if obs.value_quantity is not None
            else obs.value_string
        ),
        "summary": _build_observation_summary(obs),
        "status": obs.status,
        "category": obs.category,
        "coding": _coding_dict(obs.code),
        "details": {
            "value_quantity": _decimal_to_float(obs.value_quantity),
            "value_unit": obs.value_unit,
            "value_string": obs.value_string,
            "reference_low": _decimal_to_float(obs.reference_low),
            "reference_high": _decimal_to_float(obs.reference_high),
            "reference_text": obs.reference_text,
            "in_reference_range": obs.is_in_reference_range,
            "interpretation": obs.interpretation,
            "component_group_id": str(obs.component_group_id) if obs.component_group_id else None,
            "component_code": obs.component_code or None,
            "performer": obs.performer,
            "issued_datetime": _iso(obs.issued_datetime),
        },
        "_sort_key": (sort_dt, obs.recorded_datetime, "observation", obs.pk),
    }


def _normalize_condition(cond: Condition) -> Dict[str, Any]:
    sort_dt = cond.effective_datetime or cond.onset_datetime or cond.recorded_datetime
    display = cond.code.display
    clinical_label = cond.clinical_status.replace("-", " ").title()
    return {
        "id": f"condition:{cond.pk}",
        "resource_type": "condition",
        "resource_id": cond.pk,
        "fhir_id": str(cond.fhir_id),
        "sort_datetime": _iso(sort_dt),
        "effective_datetime": _iso(cond.effective_datetime),
        "recorded_datetime": _iso(cond.recorded_datetime),
        "title": display,
        "subtitle": clinical_label,
        "summary": f"{display} recorded as {clinical_label.lower()}",
        "status": cond.clinical_status,
        "category": "diagnosis",
        "coding": _coding_dict(cond.code),
        "details": {
            "clinical_status": cond.clinical_status,
            "verification_status": cond.verification_status,
            "severity": cond.severity or None,
            "onset_datetime": _iso(cond.onset_datetime),
            "abatement_datetime": _iso(cond.abatement_datetime),
            "asserter": cond.asserter,
        },
        "_sort_key": (sort_dt, cond.recorded_datetime, "condition", cond.pk),
    }


def _normalize_medication(med: MedicationStatement) -> Dict[str, Any]:
    sort_dt = med.effective_datetime or med.period_start
    display = med.medication_text or med.medication_code.display
    dose = ""
    if med.dose_value is not None:
        dose = f"{med.dose_value:g}"
        if med.dose_unit:
            dose = f"{dose} {med.dose_unit}"
    subtitle_parts = [p for p in [dose, med.frequency_text] if p]
    subtitle = " · ".join(subtitle_parts) if subtitle_parts else med.status.replace("-", " ").title()

    adherence_note = ""
    if med.adherence_percentage is not None:
        adherence_note = f" ({med.adherence_percentage}% adherence reported)"
    elif med.adherence_status != "unknown":
        adherence_note = f" (adherence: {med.adherence_status.replace('-', ' ')})"

    return {
        "id": f"medication:{med.pk}",
        "resource_type": "medication",
        "resource_id": med.pk,
        "fhir_id": str(med.fhir_id),
        "sort_datetime": _iso(sort_dt),
        "effective_datetime": _iso(med.effective_datetime),
        "recorded_datetime": _iso(med.recorded_datetime),
        "title": display,
        "subtitle": subtitle,
        "summary": f"Started {display}{adherence_note}".strip(),
        "status": med.status,
        "category": "medication",
        "coding": _coding_dict(med.medication_code),
        "details": {
            "dose_value": _decimal_to_float(med.dose_value),
            "dose_unit": med.dose_unit,
            "frequency_text": med.frequency_text,
            "route": med.route,
            "period_start": _iso(med.period_start),
            "period_end": _iso(med.period_end),
            "is_active": med.is_active,
            "adherence_status": med.adherence_status,
            "adherence_percentage": med.adherence_percentage,
            "adherence_recorded_at": _iso(med.adherence_recorded_at),
            "prescriber": med.prescriber,
        },
        "_sort_key": (sort_dt, med.recorded_datetime, "medication", med.pk),
    }


def _strip_internal_keys(event: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in event.items() if not k.startswith("_")}


class TimelineAggregator:
    """
    Queries clinical resources for a single patient and returns a unified,
    oldest-first timeline suitable for frontend visualization.
    """

    def __init__(self, patient: PatientUser, params: Optional[TimelineQueryParams] = None):
        self.patient = patient
        self.params = params or TimelineQueryParams()

    def aggregate(self) -> Dict[str, Any]:
        events: List[Dict[str, Any]] = []
        counts = {"observation": 0, "condition": 0, "medication": 0}

        if self._includes("observation"):
            obs_events = [_normalize_observation(o) for o in self._observation_queryset()]
            events.extend(obs_events)
            counts["observation"] = len(obs_events)

        if self._includes("condition"):
            cond_events = [_normalize_condition(c) for c in self._condition_queryset()]
            events.extend(cond_events)
            counts["condition"] = len(cond_events)

        if self._includes("medication"):
            med_events = [_normalize_medication(m) for m in self._medication_queryset()]
            events.extend(med_events)
            counts["medication"] = len(med_events)

        events.sort(key=lambda e: e["_sort_key"])
        total = len(events)

        if self.params.limit is not None and self.params.limit > 0:
            events = events[: self.params.limit]

        return {
            "patient_id": self.patient.id,
            "generated_at": _iso(timezone.now()),
            "total_events": total,
            "returned_events": len(events),
            "counts_by_type": counts,
            "filters": self._filters_payload(),
            "events": [_strip_internal_keys(e) for e in events],
        }

    def _includes(self, resource_type: str) -> bool:
        if self.params.resource_types is None:
            return True
        return resource_type in self.params.resource_types

    def _date_filter(self, field: str) -> Q:
        q = Q()
        if self.params.from_datetime:
            q &= Q(**{f"{field}__gte": self.params.from_datetime})
        if self.params.to_datetime:
            q &= Q(**{f"{field}__lte": self.params.to_datetime})
        return q

    def _observation_queryset(self) -> QuerySet[Observation]:
        qs = (
            Observation.objects.filter(patient=self.patient)
            .select_related("code")
            .order_by("effective_datetime", "recorded_datetime")
        )
        qs = qs.filter(self._date_filter("effective_datetime"))
        if not self.params.include_cancelled:
            qs = qs.exclude(status=ObservationStatus.CANCELLED)
        if self.params.observation_categories:
            qs = qs.filter(category__in=self.params.observation_categories)
        return qs

    def _condition_queryset(self) -> QuerySet[Condition]:
        return (
            Condition.objects.filter(patient=self.patient)
            .select_related("code")
            .filter(self._date_filter("effective_datetime"))
            .order_by("effective_datetime", "recorded_datetime")
        )

    def _medication_queryset(self) -> QuerySet[MedicationStatement]:
        return (
            MedicationStatement.objects.filter(patient=self.patient)
            .select_related("medication_code")
            .filter(self._date_filter("effective_datetime"))
            .order_by("effective_datetime", "recorded_datetime")
        )

    def _filters_payload(self) -> Dict[str, Any]:
        return {
            "from_datetime": _iso(self.params.from_datetime),
            "to_datetime": _iso(self.params.to_datetime),
            "resource_types": sorted(self.params.resource_types) if self.params.resource_types else None,
            "observation_categories": (
                sorted(self.params.observation_categories)
                if self.params.observation_categories
                else None
            ),
            "include_cancelled": self.params.include_cancelled,
            "limit": self.params.limit,
        }


def parse_timeline_query_params(query_params) -> TimelineQueryParams:
    """Parse and validate DRF/Django query string parameters."""
    from_dt = parse_datetime(query_params.get("from", "") or "")
    to_dt = parse_datetime(query_params.get("to", "") or "")

    if from_dt and timezone.is_naive(from_dt):
        from_dt = timezone.make_aware(from_dt, timezone=timezone.utc)
    if to_dt and timezone.is_naive(to_dt):
        to_dt = timezone.make_aware(to_dt, timezone=timezone.utc)

    types_raw = query_params.get("types", "")
    resource_types: Optional[Set[str]] = None
    if types_raw:
        requested = {t.strip().lower() for t in types_raw.split(",") if t.strip()}
        invalid = requested - TIMELINE_RESOURCE_TYPES
        if invalid:
            raise ValueError(f"Invalid resource types: {', '.join(sorted(invalid))}")
        resource_types = requested

    categories_raw = query_params.get("categories", "")
    observation_categories: Optional[Set[str]] = None
    if categories_raw:
        observation_categories = {c.strip() for c in categories_raw.split(",") if c.strip()}

    include_cancelled = query_params.get("include_cancelled", "").lower() in ("1", "true", "yes")

    limit: Optional[int] = None
    limit_raw = query_params.get("limit", "")
    if limit_raw:
        limit = int(limit_raw)
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")

    return TimelineQueryParams(
        from_datetime=from_dt,
        to_datetime=to_dt,
        resource_types=resource_types,
        observation_categories=observation_categories,
        include_cancelled=include_cancelled,
        limit=limit,
    )
