"""
Convert common Kaggle diabetes CSVs into the 11-feature format expected by train_risk_model.

Supported input formats
-----------------------
1. pima  — Pima Indians Diabetes (Kaggle: diabetes.csv)
           Columns: Pregnancies, Glucose, BloodPressure, SkinThickness,
                    Insulin, BMI, DiabetesPedigreeFunction, Age, Outcome

2. heart — UCI Heart Disease / Kaggle heart.csv
           Uses age, trestbps, chol, thalach mapped to our schema.

Usage
-----
python manage.py prepare_kaggle_csv --input path/to/diabetes.csv --format pima
python manage.py prepare_kaggle_csv --input diabetes.csv --format pima --output clinical/data/training_ready.csv
"""
from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from clinical.services.dataset_converter import (
    CONVERTERS,
    FEATURE_ORDER,
    convert_csv_to_training_rows,
    write_training_csv,
)


class Command(BaseCommand):
    help = "Convert Kaggle/UCI CSV to 11-feature training format for train_risk_model."

    def add_arguments(self, parser):
        parser.add_argument("--input", "-i", required=True, help="Path to raw Kaggle CSV.")
        parser.add_argument(
            "--format",
            "-f",
            choices=list(CONVERTERS.keys()),
            default="pima",
            help="Input dataset format (default: pima).",
        )
        parser.add_argument(
            "--output",
            "-o",
            default="clinical/data/training_ready.csv",
            help="Output path for converted CSV.",
        )

    def handle(self, *args, **options):
        input_path = Path(options["input"])
        output_path = Path(options["output"])

        if not input_path.exists():
            raise CommandError(f"Input file not found: {input_path}")

        converter_key = options["format"]
        rows_out, skipped = convert_csv_to_training_rows(input_path, converter_key)

        if len(rows_out) < 20:
            raise CommandError(
                f"Only {len(rows_out)} valid rows converted. Check --format matches your CSV columns."
            )

        write_training_csv(rows_out, output_path)

        pos_rate = sum(r["label"] for r in rows_out) / len(rows_out)
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(rows_out)} rows to {output_path}"))
        self.stdout.write(f"  Skipped:     {skipped}")
        self.stdout.write(f"  Pos. rate:   {pos_rate:.1%}")
        self.stdout.write(
            f"\nNext step:\n"
            f"  python manage.py train_risk_model --csv {output_path} --label-column label --evaluate"
        )
