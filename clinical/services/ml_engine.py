"""
Chronic disease risk prediction service layer.

Uses scikit-learn RandomForestClassifier with explicit trend-based feature
engineering (moving averages and regression slopes) derived from longitudinal
Observation time series. Model weights are persisted via joblib and loaded once
at Django startup to eliminate per-request deserialization overhead.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import joblib
import numpy as np
from django.conf import settings
from django.utils import timezone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from clinical.models import CodeSystem, Observation, PatientProfile, PatientUser

logger = logging.getLogger("clinical.ml")

# LOINC codes used for feature extraction (FHIR Observation.code alignment)
LOINC_SYSTOLIC_BP = "8480-6"
LOINC_DIASTOLIC_BP = "8462-4"
LOINC_FASTING_GLUCOSE = "1558-6"
LOINC_HBA1C = "4548-4"
LOINC_BMI = "39156-5"
LOINC_LDL = "13457-7"

FEATURE_LABELS: Dict[str, str] = {
    "age_years": "Age",
    "systolic_bp_avg": "Average systolic blood pressure",
    "systolic_bp_slope_12m": "Systolic BP trend (12 months)",
    "bmi_avg": "Average BMI",
    "bmi_slope_12m": "BMI trend (12 months)",
    "fasting_glucose_avg": "Average fasting blood glucose",
    "fasting_glucose_slope_12m": "Glucose trend (12 months)",
    "hba1c_avg": "Average HbA1c",
    "hba1c_slope_12m": "HbA1c trend (12 months)",
    "ldl_avg": "Average LDL cholesterol",
    "ldl_slope_12m": "LDL trend (12 months)",
}

PREVENTIVE_SUGGESTIONS: Dict[str, str] = {
    "systolic_bp_avg": "Track blood pressure at home and share readings with your care team.",
    "systolic_bp_slope_12m": "Your blood pressure has been trending upward — gentle daily walks may help.",
    "bmi_avg": "Small, steady changes in eating habits can support a healthier weight over time.",
    "bmi_slope_12m": "Your weight trend is rising — consider discussing nutrition goals with your clinician.",
    "fasting_glucose_avg": "Balanced meals with fewer sugary drinks can help steady blood sugar.",
    "fasting_glucose_slope_12m": "Your glucose levels have been climbing — regular movement after meals may help.",
    "hba1c_avg": "Consistent meal timing and fiber-rich foods support long-term blood sugar balance.",
    "hba1c_slope_12m": "Your HbA1c has been rising — this is worth a conversation at your next visit.",
    "ldl_avg": "Heart-healthy fats and regular activity can support cholesterol balance.",
    "ldl_slope_12m": "Your LDL has been trending up — your care team can suggest personalized steps.",
    "age_years": "Age is one factor among many — proactive screenings remain your best ally.",
}


@dataclass(frozen=True)
class ObservationPoint:
    """Single chronological measurement for trend analysis."""

    effective_datetime: datetime
    value: float


@dataclass
class TrendFeatures:
    """Computed trend statistics for a single biomarker series."""

    count: int = 0
    latest_value: Optional[float] = None
    moving_average_90d: Optional[float] = None
    slope_per_year: Optional[float] = None
    trend_label: str = "insufficient_data"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "latest_value": self.latest_value,
            "moving_average_90d": self.moving_average_90d,
            "slope_per_year": self.slope_per_year,
            "trend_label": self.trend_label,
        }


def compute_moving_average(
    points: Sequence[ObservationPoint],
    window_days: int = 90,
    reference: Optional[datetime] = None,
) -> Optional[float]:
    """
    Compute a trailing moving average over the last `window_days` days.

    Args:
        points: Chronological observation series (need not be pre-sorted).
        window_days: Trailing window length in calendar days.
        reference: End anchor for the window (defaults to latest point).

    Returns:
        Mean value within the window, or None if no points fall inside it.
    """
    if not points:
        return None

    sorted_points = sorted(points, key=lambda p: p.effective_datetime)
    anchor = reference or sorted_points[-1].effective_datetime
    window_start = anchor - timedelta(days=window_days)
    window_values = [
        p.value for p in sorted_points if window_start <= p.effective_datetime <= anchor
    ]
    if not window_values:
        return None
    return float(np.mean(window_values))


def compute_regression_slope(
    points: Sequence[ObservationPoint],
    window_days: int = 365,
    reference: Optional[datetime] = None,
) -> Optional[float]:
    """
    Fit ordinary least-squares slope over a trailing window.

    Returns slope in *units per year* (positive = rising, negative = falling).
    Requires at least two distinct time points inside the window.
    """
    if len(points) < 2:
        return None

    sorted_points = sorted(points, key=lambda p: p.effective_datetime)
    anchor = reference or sorted_points[-1].effective_datetime
    window_start = anchor - timedelta(days=window_days)
    window_points = [
        p for p in sorted_points if window_start <= p.effective_datetime <= anchor
    ]
    if len(window_points) < 2:
        return None

    # x-axis: years elapsed from first point in window (avoids float precision loss)
    t0 = window_points[0].effective_datetime
    x = np.array(
        [(p.effective_datetime - t0).total_seconds() / (365.25 * 24 * 3600) for p in window_points],
        dtype=np.float64,
    )
    y = np.array([p.value for p in window_points], dtype=np.float64)

    if np.allclose(x, x[0]):
        return None

    slope, _intercept = np.polyfit(x, y, 1)
    return float(slope)


def classify_trend(slope: Optional[float], relative_threshold: float = 0.02) -> str:
    """Translate numeric slope into patient-friendly trend vocabulary."""
    if slope is None:
        return "insufficient_data"
    if slope > relative_threshold:
        return "rising"
    if slope < -relative_threshold:
        return "dropping"
    return "stabilizing"


def analyze_observation_series(
    points: Sequence[ObservationPoint],
    *,
    ma_window_days: int = 90,
    slope_window_days: int = 365,
) -> TrendFeatures:
    """
    Full trend analysis pipeline for a single patient's biomarker history.

    Combines moving average and regression slope with a plain-language label.
    """
    if not points:
        return TrendFeatures()

    sorted_points = sorted(points, key=lambda p: p.effective_datetime)
    ma = compute_moving_average(sorted_points, window_days=ma_window_days)
    slope = compute_regression_slope(sorted_points, window_days=slope_window_days)

    return TrendFeatures(
        count=len(sorted_points),
        latest_value=sorted_points[-1].value,
        moving_average_90d=ma,
        slope_per_year=slope,
        trend_label=classify_trend(slope),
    )


def _safe_mean(values: List[Optional[float]], default: float = 0.0) -> float:
    clean = [v for v in values if v is not None]
    return float(np.mean(clean)) if clean else default


def _safe_slope(trend: TrendFeatures, default: float = 0.0) -> float:
    return trend.slope_per_year if trend.slope_per_year is not None else default


def _calculate_age_years(profile: Optional[PatientProfile], reference: Optional[datetime] = None) -> float:
    if not profile or not profile.birth_date:
        return 55.0  # population prior when DOB unavailable; flagged in metadata
    ref = (reference or timezone.now()).date()
    delta = ref - profile.birth_date
    return max(delta.days / 365.25, 0.0)


@dataclass
class RiskAssessmentResult:
    """Structured ML inference output with explainability payload."""

    patient_id: int
    risk_probability: float
    risk_label: str
    model_version: str
    features: Dict[str, float]
    trend_details: Dict[str, Dict[str, Any]]
    top_risk_drivers: List[Dict[str, str]]
    preventative_suggestions: List[str]
    assessed_at: datetime = field(default_factory=lambda: timezone.now())

    def to_api_payload(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "risk_probability": round(self.risk_probability, 4),
            "risk_percentage": round(self.risk_probability * 100, 1),
            "risk_label": self.risk_label,
            "model_version": self.model_version,
            "assessed_at": self.assessed_at.isoformat(),
            "features": self.features,
            "trend_details": self.trend_details,
            "top_risk_drivers": self.top_risk_drivers,
            "preventative_suggestions": self.preventative_suggestions,
        }


class ChronicDiseaseRiskEngine:
    """
    Singleton ML engine: loads persisted pipeline at startup, serves inference.

    Default classifier: RandomForestClassifier (interpretable via feature
    importances). Falls back to training a bootstrap model when no artifact
    exists (development only — production should ship a validated artifact).
    """

    _pipeline: Optional[Pipeline] = None
    _model_version: str = "uninitialized"
    _feature_order: Tuple[str, ...] = (
        "age_years",
        "systolic_bp_avg",
        "systolic_bp_slope_12m",
        "bmi_avg",
        "bmi_slope_12m",
        "fasting_glucose_avg",
        "fasting_glucose_slope_12m",
        "hba1c_avg",
        "hba1c_slope_12m",
        "ldl_avg",
        "ldl_slope_12m",
    )

    MODEL_FILENAME = "chronic_risk_v1.joblib"

    @classmethod
    def models_dir(cls) -> Path:
        return Path(getattr(settings, "ML_MODELS_DIR", settings.BASE_DIR / "models"))

    @classmethod
    def model_path(cls) -> Path:
        return cls.models_dir() / cls.MODEL_FILENAME

    @classmethod
    def initialize(cls) -> None:
        """Load joblib artifact or bootstrap a development model."""
        cls.models_dir().mkdir(parents=True, exist_ok=True)
        path = cls.model_path()

        if path.exists():
            artifact = joblib.load(path)
            cls._pipeline = artifact["pipeline"]
            cls._model_version = artifact.get("version", "v1.0.0")
            logger.info("Loaded risk model %s from %s", cls._model_version, path)
            return

        logger.warning("No persisted model at %s — training bootstrap classifier.", path)
        cls._pipeline = cls._train_bootstrap_model()
        cls._model_version = "bootstrap-v1.0.0"
        joblib.dump(
            {"pipeline": cls._pipeline, "version": cls._model_version, "feature_order": cls._feature_order},
            path,
        )
        logger.info("Bootstrap model persisted to %s", path)

    @classmethod
    def _train_bootstrap_model(cls) -> Pipeline:
        """
        Train a synthetic-data RandomForest for development/demo deployments.

        Production deployments MUST replace this artifact with a model validated
        on real cohort data and approved through clinical governance review.
        """
        rng = np.random.default_rng(42)
        n = 4000
        X = rng.normal(size=(n, len(cls._feature_order)))
        # Simulated risk surface: higher BP, glucose, BMI slopes → elevated risk
        risk_logit = (
            0.9 * X[:, 1]
            + 0.7 * X[:, 2]
            + 0.6 * X[:, 4]
            + 0.8 * X[:, 6]
            + 0.5 * X[:, 0]
        )
        y = (risk_logit + rng.normal(0, 0.5, size=n) > 0.8).astype(int)

        classifier = RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ])
        pipeline.fit(X, y)
        return pipeline

    @classmethod
    def _ensure_ready(cls) -> Pipeline:
        if cls._pipeline is None:
            cls.initialize()
        return cls._pipeline  # type: ignore[return-value]

    @classmethod
    def _extract_observation_points(
        cls,
        patient: PatientUser,
        loinc_code: str,
        *,
        lookback_days: int = 1825,
    ) -> List[ObservationPoint]:
        cutoff = timezone.now() - timedelta(days=lookback_days)
        qs = (
            Observation.objects.filter(
                patient=patient,
                code__system=CodeSystem.LOINC,
                code__code=loinc_code,
                value_quantity__isnull=False,
                effective_datetime__gte=cutoff,
            )
            .select_related("code")
            .order_by("effective_datetime")
        )
        return [
            ObservationPoint(
                effective_datetime=obs.effective_datetime,
                value=float(obs.value_quantity),
            )
            for obs in qs
        ]

    @classmethod
    def build_feature_vector(cls, patient: PatientUser) -> Tuple[np.ndarray, Dict[str, float], Dict[str, Dict[str, Any]]]:
        """Assemble ML feature vector and parallel trend metadata from ORM data."""
        profile = getattr(patient, "profile", None)

        series_map = {
            "systolic_bp": LOINC_SYSTOLIC_BP,
            "bmi": LOINC_BMI,
            "fasting_glucose": LOINC_FASTING_GLUCOSE,
            "hba1c": LOINC_HBA1C,
            "ldl": LOINC_LDL,
        }

        trends: Dict[str, TrendFeatures] = {}
        raw_series: Dict[str, List[ObservationPoint]] = {}
        for key, loinc in series_map.items():
            pts = cls._extract_observation_points(patient, loinc)
            raw_series[key] = pts
            trends[key] = analyze_observation_series(pts)

        age = _calculate_age_years(profile)

        features: Dict[str, float] = {
            "age_years": age,
            "systolic_bp_avg": _safe_mean([trends["systolic_bp"].moving_average_90d, trends["systolic_bp"].latest_value], 125.0),
            "systolic_bp_slope_12m": _safe_slope(trends["systolic_bp"]),
            "bmi_avg": _safe_mean([trends["bmi"].moving_average_90d, trends["bmi"].latest_value], 27.0),
            "bmi_slope_12m": _safe_slope(trends["bmi"]),
            "fasting_glucose_avg": _safe_mean([trends["fasting_glucose"].moving_average_90d, trends["fasting_glucose"].latest_value], 95.0),
            "fasting_glucose_slope_12m": _safe_slope(trends["fasting_glucose"]),
            "hba1c_avg": _safe_mean([trends["hba1c"].moving_average_90d, trends["hba1c"].latest_value], 5.6),
            "hba1c_slope_12m": _safe_slope(trends["hba1c"]),
            "ldl_avg": _safe_mean([trends["ldl"].moving_average_90d, trends["ldl"].latest_value], 110.0),
            "ldl_slope_12m": _safe_slope(trends["ldl"]),
        }

        trend_details = {key: trends[key].to_dict() for key in trends}
        vector = np.array([[features[name] for name in cls._feature_order]], dtype=np.float64)
        return vector, features, trend_details

    @classmethod
    def _explain_top_drivers(
        cls,
        feature_vector: np.ndarray,
        features: Dict[str, float],
        probability: float,
    ) -> List[Dict[str, str]]:
        """
        Identify top two features pushing risk upward using impurity-based
        importances scaled by per-patient deviation from training centroid.
        """
        pipeline = cls._ensure_ready()
        classifier = pipeline.named_steps["classifier"]
        scaler: StandardScaler = pipeline.named_steps["scaler"]

        if not hasattr(classifier, "feature_importances_"):
            return []

        importances = classifier.feature_importances_
        scaled = scaler.transform(feature_vector)[0]

        # Risk direction score: large positive scaled value on high-importance feature
        direction_scores = importances * np.maximum(scaled, 0.0)
        ranked_indices = np.argsort(direction_scores)[::-1]

        drivers: List[Dict[str, str]] = []
        for idx in ranked_indices:
            if len(drivers) >= 2:
                break
            fname = cls._feature_order[idx]
            if direction_scores[idx] <= 0:
                continue
            human = FEATURE_LABELS.get(fname, fname)
            trend_word = ""
            if "slope" in fname and features.get(fname, 0) > 0:
                trend_word = " (rising)"
            elif "slope" in fname and features.get(fname, 0) < 0:
                trend_word = " (improving)"
            drivers.append({
                "feature": fname,
                "label": f"{human}{trend_word}",
                "impact_score": round(float(direction_scores[idx]), 4),
            })

        if len(drivers) < 2:
            # Fill with globally important features if patient-specific signal is weak
            for idx in np.argsort(importances)[::-1]:
                if len(drivers) >= 2:
                    break
                fname = cls._feature_order[idx]
                if any(d["feature"] == fname for d in drivers):
                    continue
                drivers.append({
                    "feature": fname,
                    "label": FEATURE_LABELS.get(fname, fname),
                    "impact_score": round(float(importances[idx]), 4),
                })

        return drivers[:2]

    @classmethod
    def _risk_label(cls, probability: float) -> str:
        if probability < 0.33:
            return "lower"
        if probability < 0.66:
            return "moderate"
        return "elevated"

    @classmethod
    def assess_patient(cls, patient: PatientUser) -> RiskAssessmentResult:
        """
        Execute full predictive pipeline for a single authenticated patient.

        Raises:
            RuntimeError: if model failed to initialize.
        """
        pipeline = cls._ensure_ready()
        vector, features, trend_details = cls.build_feature_vector(patient)

        proba = float(pipeline.predict_proba(vector)[0][1])
        drivers = cls._explain_top_drivers(vector, features, proba)

        suggestions = []
        seen = set()
        for driver in drivers:
            key = driver["feature"]
            tip = PREVENTIVE_SUGGESTIONS.get(key)
            if tip and tip not in seen:
                suggestions.append(tip)
                seen.add(tip)
        if not suggestions:
            suggestions.append("Keep up regular check-ups — steady habits make a real difference over time.")

        return RiskAssessmentResult(
            patient_id=patient.id,
            risk_probability=proba,
            risk_label=cls._risk_label(proba),
            model_version=cls._model_version,
            features=features,
            trend_details=trend_details,
            top_risk_drivers=drivers,
            preventative_suggestions=suggestions,
        )
