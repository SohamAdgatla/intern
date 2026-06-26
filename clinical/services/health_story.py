"""
Health Story Engine — rule-based plain-language narratives for patients.

Translates longitudinal numeric trends (e.g. a 15% LDL drop over six months)
into warm, jargon-free summaries suitable for elderly patients and chronic-care
self-management. Pure Python rules — no LLM dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

from clinical.models import CodeSystem, Observation, PatientUser
from clinical.services.ml_engine import (
    LOINC_BMI,
    LOINC_FASTING_GLUCOSE,
    LOINC_HBA1C,
    LOINC_LDL,
    LOINC_SYSTOLIC_BP,
    ObservationPoint,
    analyze_observation_series,
)


# ---------------------------------------------------------------------------
# Biomarker configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BiomarkerConfig:
    loinc_code: str
    friendly_name: str
    unit: str
    lower_is_better: bool = True
    stable_threshold_pct: float = 3.0
    notable_threshold_pct: float = 5.0
    significant_threshold_pct: float = 10.0


BIOMARKERS: Tuple[BiomarkerConfig, ...] = (
    BiomarkerConfig(LOINC_LDL, "LDL cholesterol", "mg/dL"),
    BiomarkerConfig(LOINC_HBA1C, "HbA1c", "%"),
    BiomarkerConfig(LOINC_SYSTOLIC_BP, "blood pressure (top number)", "mmHg"),
    BiomarkerConfig(LOINC_FASTING_GLUCOSE, "fasting blood sugar", "mg/dL"),
    BiomarkerConfig(LOINC_BMI, "BMI", ""),
)


def _months_between(start: datetime, end: datetime) -> float:
    return max((end - start).days / 30.44, 0.1)


def _format_value(value: float, unit: str) -> str:
    rounded = round(value, 1) if value < 100 else round(value)
    return f"{rounded}{f' {unit}' if unit else ''}"


def _format_months(months: float) -> str:
    if months < 1.5:
        return "about a month"
    rounded = round(months)
    if rounded == 1:
        return "about 1 month"
    if rounded < 12:
        return f"about {rounded} months"
    years = round(months / 12, 1)
    if years == 1:
        return "about a year"
    return f"about {years} years"


@dataclass
class PeriodChange:
    """Numeric change between two clinical time points."""

    start_value: float
    end_value: float
    start_date: datetime
    end_date: datetime
    percent_change: float
    months_span: float
    direction: str  # improving | worsening | stable

    @property
    def absolute_change(self) -> float:
        return self.end_value - self.start_value


@dataclass
class BiomarkerStory:
    """Single-biomarker narrative fragment."""

    loinc_code: str
    friendly_name: str
    change: Optional[PeriodChange]
    trend_label: str
    latest_value: Optional[float]
    in_reference_range: Optional[bool]
    narrative: str
    tone: str  # positive | neutral | attentive

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loinc_code": self.loinc_code,
            "friendly_name": self.friendly_name,
            "narrative": self.narrative,
            "tone": self.tone,
            "trend_label": self.trend_label,
            "latest_value": self.latest_value,
            "in_reference_range": self.in_reference_range,
            "change": (
                {
                    "start_value": self.change.start_value,
                    "end_value": self.change.end_value,
                    "percent_change": round(self.change.percent_change, 1),
                    "months_span": round(self.change.months_span, 1),
                    "direction": self.change.direction,
                }
                if self.change
                else None
            ),
        }


@dataclass
class HealthStoryResult:
    """Complete health story payload for API consumption."""

    patient_id: int
    headline: str
    overview: str
    paragraphs: List[str]
    highlights: List[BiomarkerStory]
    encouragement: str
    lookback_months: int
    generated_at: datetime = field(default_factory=lambda: timezone.now())

    def to_api_payload(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "headline": self.headline,
            "overview": self.overview,
            "paragraphs": self.paragraphs,
            "highlights": [h.to_dict() for h in self.highlights],
            "encouragement": self.encouragement,
            "lookback_months": self.lookback_months,
            "generated_at": self.generated_at.isoformat(),
        }


class HealthStoryEngine:
    """
    Rule engine that inspects multi-year observation history and composes
    empathetic, plain-language health stories for the patient portal.
    """

    DEFAULT_LOOKBACK_DAYS = 365 * 3

    def __init__(self, patient: PatientUser, lookback_months: int = 24):
        self.patient = patient
        self.lookback_months = lookback_months
        self.lookback_days = lookback_months * 30

    def generate(self) -> HealthStoryResult:
        stories: List[BiomarkerStory] = []
        for config in BIOMARKERS:
            points = self._load_points(config.loinc_code)
            if len(points) >= 1:
                stories.append(self._build_biomarker_story(config, points))

        meaningful = [s for s in stories if s.change or s.trend_label != "insufficient_data"]
        headline = self._compose_headline(meaningful)
        overview = self._compose_overview(meaningful)
        paragraphs = self._compose_paragraphs(meaningful)
        encouragement = self._compose_encouragement(meaningful)

        return HealthStoryResult(
            patient_id=self.patient.id,
            headline=headline,
            overview=overview,
            paragraphs=paragraphs,
            highlights=stories,
            encouragement=encouragement,
            lookback_months=self.lookback_months,
        )

    def _load_points(self, loinc_code: str) -> List[ObservationPoint]:
        cutoff = timezone.now() - timedelta(days=self.lookback_days)
        qs = (
            Observation.objects.filter(
                patient=self.patient,
                code__system=CodeSystem.LOINC,
                code__code=loinc_code,
                value_quantity__isnull=False,
                effective_datetime__gte=cutoff,
            )
            .select_related("code")
            .order_by("effective_datetime")
        )
        return [
            ObservationPoint(effective_datetime=obs.effective_datetime, value=float(obs.value_quantity))
            for obs in qs
        ]

    def _latest_reference_status(self, loinc_code: str) -> Tuple[Optional[float], Optional[bool]]:
        obs = (
            Observation.objects.filter(
                patient=self.patient,
                code__system=CodeSystem.LOINC,
                code__code=loinc_code,
                value_quantity__isnull=False,
            )
            .order_by("-effective_datetime")
            .first()
        )
        if not obs:
            return None, None
        return float(obs.value_quantity), obs.is_in_reference_range

    def _compute_period_change(
        self,
        points: List[ObservationPoint],
        config: BiomarkerConfig,
    ) -> Optional[PeriodChange]:
        if len(points) < 2:
            return None

        sorted_pts = sorted(points, key=lambda p: p.effective_datetime)
        start_pt, end_pt = sorted_pts[0], sorted_pts[-1]

        if start_pt.value == 0:
            return None

        raw_pct = ((end_pt.value - start_pt.value) / abs(start_pt.value)) * 100
        months = _months_between(start_pt.effective_datetime, end_pt.effective_datetime)

        if config.lower_is_better:
            if raw_pct <= -config.stable_threshold_pct:
                direction = "improving"
            elif raw_pct >= config.stable_threshold_pct:
                direction = "worsening"
            else:
                direction = "stable"
        else:
            if raw_pct >= config.stable_threshold_pct:
                direction = "improving"
            elif raw_pct <= -config.stable_threshold_pct:
                direction = "worsening"
            else:
                direction = "stable"

        return PeriodChange(
            start_value=start_pt.value,
            end_value=end_pt.value,
            start_date=start_pt.effective_datetime,
            end_date=end_pt.effective_datetime,
            percent_change=raw_pct,
            months_span=months,
            direction=direction,
        )

    def _build_biomarker_story(
        self,
        config: BiomarkerConfig,
        points: List[ObservationPoint],
    ) -> BiomarkerStory:
        trend = analyze_observation_series(points, slope_window_days=min(self.lookback_days, 365))
        change = self._compute_period_change(points, config)
        latest_value, in_range = self._latest_reference_status(config.loinc_code)

        narrative = self._rule_narrative(config, change, trend.trend_label, latest_value, in_range)
        tone = self._tone_for(change, in_range)

        return BiomarkerStory(
            loinc_code=config.loinc_code,
            friendly_name=config.friendly_name,
            change=change,
            trend_label=trend.trend_label,
            latest_value=latest_value,
            in_reference_range=in_range,
            narrative=narrative,
            tone=tone,
        )

    def _rule_narrative(
        self,
        config: BiomarkerConfig,
        change: Optional[PeriodChange],
        trend_label: str,
        latest_value: Optional[float],
        in_range: Optional[bool],
    ) -> str:
        name = config.friendly_name

        if change is None and latest_value is None:
            return f"We don't have enough recent {name} readings to tell a story yet."

        if change is None:
            val_text = _format_value(latest_value, config.unit)
            range_note = ""
            if in_range is True:
                range_note = " — right where your care team likes to see it."
            elif in_range is False:
                range_note = " — your clinician can help you understand what this means for you."
            return f"Your most recent {name} reading is {val_text}{range_note}"

        pct = abs(change.percent_change)
        span = _format_months(change.months_span)
        start_text = _format_value(change.start_value, config.unit)
        end_text = _format_value(change.end_value, config.unit)

        # --- Improving ---
        if change.direction == "improving":
            if pct >= config.significant_threshold_pct:
                return (
                    f"Your {name} has come down by about {pct:.0f}% over the past {span} "
                    f"(from {start_text} to {end_text}). That's a meaningful shift, and it shows "
                    f"your steady efforts may be paying off."
                )
            if pct >= config.notable_threshold_pct:
                return (
                    f"Your {name} has gently improved over the past {span}, dropping about "
                    f"{pct:.0f}% (from {start_text} to {end_text}). Small steps like this add up."
                )
            return (
                f"Your {name} has edged in a good direction over the past {span} "
                f"({start_text} → {end_text})."
            )

        # --- Worsening ---
        if change.direction == "worsening":
            if pct >= config.significant_threshold_pct:
                return (
                    f"Your {name} has risen about {pct:.0f}% over the past {span} "
                    f"(from {start_text} to {end_text}). This is worth a calm conversation with "
                    f"your care team — together you can choose next steps that feel manageable."
                )
            if pct >= config.notable_threshold_pct:
                return (
                    f"Your {name} has crept up a little over the past {span} "
                    f"(about {pct:.0f}%, from {start_text} to {end_text}). "
                    f"Catching these shifts early is one of the best things you can do."
                )
            return (
                f"Your {name} has moved slightly upward over the past {span} "
                f"({start_text} → {end_text}). Keep tracking — patterns over time matter most."
            )

        # --- Stable ---
        stable_line = (
            f"Your {name} has stayed fairly steady over the past {span} "
            f"(around {start_text} to {end_text}). Consistency can be a quiet win."
        )
        if trend_label == "rising":
            stable_line += " Recent readings suggest a slight upward drift — worth keeping an eye on."
        elif trend_label == "dropping":
            stable_line += " Lately things have been gently trending down, which is encouraging."
        return stable_line

    @staticmethod
    def _tone_for(change: Optional[PeriodChange], in_range: Optional[bool]) -> str:
        if change and change.direction == "improving":
            return "positive"
        if change and change.direction == "worsening":
            return "attentive"
        if in_range is False:
            return "attentive"
        return "neutral"

    def _compose_headline(self, stories: List[BiomarkerStory]) -> str:
        improving = [s for s in stories if s.change and s.change.direction == "improving"]
        worsening = [s for s in stories if s.change and s.change.direction == "worsening"]

        if improving and not worsening:
            return "Your health numbers are moving in an encouraging direction"
        if improving and worsening:
            return "Your health story shows progress in some areas and room to grow in others"
        if worsening and not improving:
            return "We're keeping a caring eye on a few of your health trends"
        return "Here is a calm snapshot of your health over time"

    def _compose_overview(self, stories: List[BiomarkerStory]) -> str:
        if not stories:
            return (
                "As labs, vitals, and visits are recorded, this space will fill with a clear, "
                "chronological story written just for you — without confusing medical jargon."
            )

        improving = sum(1 for s in stories if s.change and s.change.direction == "improving")
        worsening = sum(1 for s in stories if s.change and s.change.direction == "worsening")
        span = _format_months(self.lookback_months)

        parts = [f"Over the past {span}, we've looked at how your key health numbers have changed."]

        if improving:
            parts.append(
                f"{improving} area{'s' if improving != 1 else ''} show improvement."
            )
        if worsening:
            parts.append(
                f"{worsening} area{'s' if worsening != 1 else ''} deserve a little extra attention — "
                "not as a scare, but as a chance to plan ahead."
            )
        if not improving and not worsening:
            parts.append("Most of your numbers have held steady, which is often a sign of stability.")

        return " ".join(parts)

    def _compose_paragraphs(self, stories: List[BiomarkerStory]) -> List[str]:
        if not stories:
            return []

        narratives = [s.narrative for s in stories if s.narrative]
        if not narratives:
            return []

        paragraphs: List[str] = []
        chunk_size = 2
        for i in range(0, len(narratives), chunk_size):
            chunk = narratives[i : i + chunk_size]
            paragraphs.append(" ".join(chunk))

        return paragraphs

    def _compose_encouragement(self, stories: List[BiomarkerStory]) -> str:
        improving = [s for s in stories if s.change and s.change.direction == "improving"]
        worsening = [s for s in stories if s.change and s.change.direction == "worsening"]

        if improving:
            names = ", ".join(s.friendly_name for s in improving[:2])
            return (
                f"Changes in {names} didn't happen overnight — they reflect the care you're "
                f"putting into yourself. Celebrate the progress, and bring questions to your "
                f"next visit. You don't have to figure this out alone."
            )
        if worsening:
            return (
                "Noticing a trend early is an act of self-care, not a failure. Your care team is "
                "here to help you choose small, realistic steps. One appointment, one habit, one "
                "day at a time is enough."
            )
        return (
            "Showing up to track your health — and reading a summary like this — is already a "
            "positive step. Keep your regular check-ups, and never hesitate to ask questions in "
            "words that make sense to you."
        )
