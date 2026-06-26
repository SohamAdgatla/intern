"""
Convert external CSV datasets into the 11-feature ML training format.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from clinical.services.ml_engine import ChronicDiseaseRiskEngine

FEATURE_ORDER = list(ChronicDiseaseRiskEngine._feature_order)


def _glucose_to_hba1c_estimate(glucose_mg_dl: float) -> float:
    return round((glucose_mg_dl + 46.7) / 28.7, 2)


def _estimate_ldl(bmi: float, glucose: float) -> float:
    return round(90 + 0.8 * max(bmi - 25, 0) + 0.05 * max(glucose - 100, 0), 1)


def convert_pima_row(row: dict) -> dict:
    glucose = float(row.get("Glucose") or row.get("glucose") or 0)
    bp = float(row.get("BloodPressure") or row.get("blood_pressure") or row.get("Blood Pressure") or 120)
    bmi = float(row.get("BMI") or row.get("bmi") or 27)
    age = float(row.get("Age") or row.get("age") or 50)
    label = int(float(row.get("Outcome") or row.get("outcome") or row.get("label") or 0))
    hba1c = _glucose_to_hba1c_estimate(glucose)
    ldl = _estimate_ldl(bmi, glucose)
    return {
        "age_years": age,
        "systolic_bp_avg": bp,
        "systolic_bp_slope_12m": 0.0,
        "bmi_avg": bmi,
        "bmi_slope_12m": 0.0,
        "fasting_glucose_avg": glucose,
        "fasting_glucose_slope_12m": 0.0,
        "hba1c_avg": hba1c,
        "hba1c_slope_12m": 0.0,
        "ldl_avg": ldl,
        "ldl_slope_12m": 0.0,
        "label": label,
    }


def convert_heart_row(row: dict) -> dict:
    age = float(row.get("age") or row.get("Age") or 55)
    bp = float(row.get("trestbps") or row.get("resting_blood_pressure") or 130)
    chol = float(row.get("chol") or row.get("cholesterol") or 200)
    raw_target = row.get("target") or row.get("Target") or row.get("num") or 0
    label = 1 if int(float(raw_target)) > 0 else 0
    glucose = 95.0
    return {
        "age_years": age,
        "systolic_bp_avg": bp,
        "systolic_bp_slope_12m": 0.0,
        "bmi_avg": 26.0,
        "bmi_slope_12m": 0.0,
        "fasting_glucose_avg": glucose,
        "fasting_glucose_slope_12m": 0.0,
        "hba1c_avg": _glucose_to_hba1c_estimate(glucose),
        "hba1c_slope_12m": 0.0,
        "ldl_avg": min(float(chol), 250),
        "ldl_slope_12m": 0.0,
        "label": label,
    }


def convert_diabetes_row(row: dict) -> dict:
    age = float(row.get("age") or row.get("Age") or 50)
    bmi = float(row.get("bmi") or row.get("BMI") or 27)
    glucose = float(
        row.get("blood_glucose_level")
        or row.get("blood_glucose")
        or row.get("glucose")
        or 100
    )
    hba1c = float(
        row.get("HbA1c_level")
        or row.get("hba1c_level")
        or row.get("hba1c")
        or _glucose_to_hba1c_estimate(glucose)
    )
    hypertension = row.get("hypertension") or row.get("Hypertension") or 0
    try:
        hypertension_flag = int(float(hypertension))
    except (ValueError, TypeError):
        hypertension_flag = 0
    bp = 150.0 if hypertension_flag else 120.0
    ldl = _estimate_ldl(bmi, glucose)
    label_value = row.get("diabetes") or row.get("Diabetes") or row.get("label") or 0
    label = int(float(label_value))
    return {
        "age_years": age,
        "systolic_bp_avg": bp,
        "systolic_bp_slope_12m": 0.0,
        "bmi_avg": bmi,
        "bmi_slope_12m": 0.0,
        "fasting_glucose_avg": glucose,
        "fasting_glucose_slope_12m": 0.0,
        "hba1c_avg": hba1c,
        "hba1c_slope_12m": 0.0,
        "ldl_avg": ldl,
        "ldl_slope_12m": 0.0,
        "label": label,
    }


CONVERTERS: Dict[str, Callable[[dict], dict]] = {
    "pima": convert_pima_row,
    "heart": convert_heart_row,
    "diabetes": convert_diabetes_row,
}


def detect_dataset_format(headers: List[str]) -> str:
    """Guess dataset format from CSV column headers."""
    normalized = {h.strip().lower() for h in headers}
    if "age_years" in normalized and "label" in normalized:
        return "ready"
    if "glucose" in normalized and ("outcome" in normalized or "label" in normalized):
        return "pima"
    if "trestbps" in normalized and ("target" in normalized or "num" in normalized):
        return "heart"
    if "bloodpressure" in normalized or "blood pressure" in normalized:
        return "pima"
    if "hba1c_level" in normalized and "blood_glucose_level" in normalized:
        return "diabetes"
    raise ValueError(
        f"Could not detect dataset format. Columns found: {headers}. "
        "Supported: Pima (Glucose, BloodPressure, BMI, Age, Outcome), "
        "Heart (age, trestbps, chol, target), Diabetes (age, BMI, HbA1c_level, blood_glucose_level, diabetes), "
        "or pre-converted 11-feature CSV with 'label'."
    )


def convert_csv_to_training_rows(
    input_path: Path,
    fmt: str,
) -> Tuple[List[dict], int]:
    """Convert raw or ready CSV to list of training row dicts."""
    skipped = 0
    rows_out: List[dict] = []

    with input_path.open(newline="", encoding="utf-8-sig") as infile:
        reader = csv.DictReader(infile)
        headers = reader.fieldnames or []

        if fmt == "ready":
            for row in reader:
                try:
                    features = {col: float(row[col]) for col in FEATURE_ORDER}
                    features["label"] = int(float(row["label"]))
                    if features["label"] not in (0, 1):
                        skipped += 1
                        continue
                    rows_out.append(features)
                except (KeyError, ValueError, TypeError):
                    skipped += 1
            return rows_out, skipped

        converter = CONVERTERS[fmt]
        for row in reader:
            try:
                features = converter(row)
                if features["label"] not in (0, 1):
                    skipped += 1
                    continue
                rows_out.append(features)
            except (ValueError, TypeError):
                skipped += 1

    return rows_out, skipped


def write_training_csv(rows: List[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = FEATURE_ORDER + ["label"]
    with output_path.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def inspect_dataset(input_path: Path) -> dict:
    """Return metadata about a dataset file for CLI display."""
    with input_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        row_count = sum(1 for _ in reader)
    fmt = detect_dataset_format(headers) if headers else "unknown"
    return {"headers": headers, "row_count": row_count, "format": fmt}
