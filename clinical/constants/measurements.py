"""
Default LOINC measurement types for patient self-entry.
"""
from __future__ import annotations

from typing import Any, Dict, List

MEASUREMENT_TYPES: List[Dict[str, Any]] = [
    {
        "loinc_code": "4548-4",
        "display": "HbA1c",
        "category": "laboratory",
        "unit": "%",
        "reference_low": 4.0,
        "reference_high": 5.6,
    },
    {
        "loinc_code": "8480-6",
        "display": "Systolic blood pressure",
        "category": "vital-signs",
        "unit": "mmHg",
        "reference_low": 90,
        "reference_high": 120,
    },
    {
        "loinc_code": "8462-4",
        "display": "Diastolic blood pressure",
        "category": "vital-signs",
        "unit": "mmHg",
        "reference_low": 60,
        "reference_high": 80,
    },
    {
        "loinc_code": "1558-6",
        "display": "Fasting blood glucose",
        "category": "laboratory",
        "unit": "mg/dL",
        "reference_low": 70,
        "reference_high": 99,
    },
    {
        "loinc_code": "13457-7",
        "display": "LDL cholesterol",
        "category": "laboratory",
        "unit": "mg/dL",
        "reference_low": 0,
        "reference_high": 100,
    },
    {
        "loinc_code": "39156-5",
        "display": "BMI",
        "category": "vital-signs",
        "unit": "kg/m2",
        "reference_low": 18.5,
        "reference_high": 24.9,
    },
    {
        "loinc_code": "8867-4",
        "display": "Heart rate",
        "category": "vital-signs",
        "unit": "bpm",
        "reference_low": 60,
        "reference_high": 100,
    },
]
