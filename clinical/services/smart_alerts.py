"""
Smart Alerts — rule-based longitudinal pattern detection with plain-language messaging.

Detects clinically meaningful trends (rising BP, adherence gaps, weight patterns)
without alarmist jargon. Designed for elderly and low digital-literacy patients.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.utils import timezone

from clinical.models import (
    AdherenceStatus,
    CodeSystem,
    MedicationStatement,
    MedicationStatus,
    Observation,
    PatientUser,
)
from clinical.services.ml_engine import (
    LOINC_BMI,
    LOINC_HBA1C,
    LOINC_SYSTOLIC_BP,
    ObservationPoint,
    analyze_observation_series,
    compute_regression_slope,
)


@dataclass
class SmartAlert:
    id: str
    severity: str  # info | watch | attention
    category: str  # vitals | medication | labs | lifestyle
    title: str
    message: str
    action_hint: str
    detected_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "message": self.message,
            "action_hint": self.action_hint,
            "detected_at": self.detected_at,
            "metadata": self.metadata,
        }


class SmartAlertEngine:
    """Evaluates multi-year patient data and returns prioritized smart alerts."""

    LOOKBACK_DAYS = 365

    def __init__(self, patient: PatientUser):
        self.patient = patient
        self.now = timezone.now()

    def evaluate(self) -> Dict[str, Any]:
        alerts: List[SmartAlert] = []
        alerts.extend(self._check_rising_vitals())
        alerts.extend(self._check_medication_adherence())
        alerts.extend(self._check_lab_trends())
        alerts.extend(self._check_weight_pattern())

        severity_order = {"attention": 0, "watch": 1, "info": 2}
        alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

        return {
            "patient_id": self.patient.id,
            "generated_at": self.now.isoformat(),
            "alert_count": len(alerts),
            "alerts": [a.to_dict() for a in alerts],
        }

    def _load_points(self, loinc_code: str) -> List[ObservationPoint]:
        cutoff = self.now - timedelta(days=self.LOOKBACK_DAYS * 3)
        qs = Observation.objects.filter(
            patient=self.patient,
            code__system=CodeSystem.LOINC,
            code__code=loinc_code,
            value_quantity__isnull=False,
            effective_datetime__gte=cutoff,
        ).order_by("effective_datetime")
        return [
            ObservationPoint(effective_datetime=o.effective_datetime, value=float(o.value_quantity))
            for o in qs
        ]

    def _check_rising_vitals(self) -> List[SmartAlert]:
        alerts = []
        points = self._load_points(LOINC_SYSTOLIC_BP)
        if len(points) < 3:
            return alerts

        slope = compute_regression_slope(points, window_days=180)
        trend = analyze_observation_series(points, slope_window_days=180)

        if slope is not None and slope > 1.5 and trend.trend_label == "rising":
            alerts.append(
                SmartAlert(
                    id="bp-rising-6m",
                    severity="watch",
                    category="vitals",
                    title="Blood pressure has been creeping up",
                    message=(
                        "Your top blood pressure number has been gradually rising over the "
                        "past several months. This doesn't mean something is wrong — but it's "
                        "worth keeping an eye on."
                    ),
                    action_hint="Try logging home readings and share them at your next visit.",
                    detected_at=self.now.isoformat(),
                    metadata={"slope_per_year": round(slope, 2), "trend": trend.trend_label},
                )
            )
        return alerts

    def _check_medication_adherence(self) -> List[SmartAlert]:
        alerts = []
        meds = MedicationStatement.objects.filter(
            patient=self.patient,
            status=MedicationStatus.ACTIVE,
        ).select_related("medication_code")

        for med in meds:
            if med.adherence_status in (AdherenceStatus.PARTIAL, AdherenceStatus.NOT_TAKING):
                name = med.medication_text or med.medication_code.display
                alerts.append(
                    SmartAlert(
                        id=f"adherence-{med.pk}",
                        severity="attention",
                        category="medication",
                        title=f"Medication adherence needs support",
                        message=(
                            f"It looks like taking {name} as prescribed has been difficult lately. "
                            f"Many people face this — you're not alone."
                        ),
                        action_hint="Ask your pharmacist about pill organizers or reminder apps.",
                        detected_at=self.now.isoformat(),
                        metadata={
                            "medication": name,
                            "adherence_status": med.adherence_status,
                            "adherence_percentage": med.adherence_percentage,
                        },
                    )
                )
            elif med.adherence_percentage is not None and med.adherence_percentage < 70:
                name = med.medication_text or med.medication_code.display
                alerts.append(
                    SmartAlert(
                        id=f"adherence-pct-{med.pk}",
                        severity="watch",
                        category="medication",
                        title="Medication routine could use a boost",
                        message=(
                            f"Your reported adherence for {name} is around {med.adherence_percentage}%. "
                            f"Small reminders can make a big difference."
                        ),
                        action_hint="Link your medication to a daily habit like breakfast.",
                        detected_at=self.now.isoformat(),
                        metadata={"medication": name, "adherence_percentage": med.adherence_percentage},
                    )
                )
        return alerts

    def _check_lab_trends(self) -> List[SmartAlert]:
        alerts = []
        points = self._load_points(LOINC_HBA1C)
        if len(points) < 2:
            return alerts

        trend = analyze_observation_series(points, slope_window_days=365)
        if trend.trend_label == "rising" and trend.slope_per_year and trend.slope_per_year > 0.1:
            alerts.append(
                SmartAlert(
                    id="hba1c-rising",
                    severity="watch",
                    category="labs",
                    title="Blood sugar average is trending upward",
                    message=(
                        "Your HbA1c — a measure of average blood sugar over time — has been "
                        "moving in the wrong direction. Catching this early gives you and your "
                        "care team more options."
                    ),
                    action_hint="Review meal timing and activity with your clinician.",
                    detected_at=self.now.isoformat(),
                    metadata={"trend": trend.trend_label, "latest": trend.latest_value},
                )
            )
        elif trend.trend_label == "dropping":
            alerts.append(
                SmartAlert(
                    id="hba1c-improving",
                    severity="info",
                    category="labs",
                    title="Blood sugar control is improving",
                    message=(
                        "Your HbA1c has been trending down — that's encouraging progress. "
                        "Whatever you're doing, keep the conversation going with your care team."
                    ),
                    action_hint="Celebrate small wins and stay consistent.",
                    detected_at=self.now.isoformat(),
                    metadata={"trend": trend.trend_label, "latest": trend.latest_value},
                )
            )
        return alerts

    def _check_weight_pattern(self) -> List[SmartAlert]:
        alerts = []
        points = self._load_points(LOINC_BMI)
        if len(points) < 3:
            return alerts

        slope = compute_regression_slope(points, window_days=365)
        if slope is not None and slope > 0.3:
            alerts.append(
                SmartAlert(
                    id="bmi-gain-pattern",
                    severity="watch",
                    category="lifestyle",
                    title="Weight trend moving upward",
                    message=(
                        "Over the past year, your BMI has shown a gradual upward pattern. "
                        "Bodies change — what matters is noticing the trend and discussing "
                        "goals that feel realistic for you."
                    ),
                    action_hint="Consider gentle daily movement and balanced meals.",
                    detected_at=self.now.isoformat(),
                    metadata={"slope_per_year": round(slope, 2)},
                )
            )
        return alerts
