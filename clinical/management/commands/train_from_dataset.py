"""
One-step training: place your CSV in clinical/data/, run this command.

Examples
--------
python manage.py train_from_dataset --input clinical/data/diabetes.csv
python manage.py train_from_dataset --input clinical/data/diabetes.csv --format pima --evaluate
python manage.py train_from_dataset --input clinical/data/training_ready.csv --from-db --evaluate
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from clinical.services.dataset_converter import (
    convert_csv_to_training_rows,
    detect_dataset_format,
    inspect_dataset,
    write_training_csv,
)


class Command(BaseCommand):
    help = "Auto-detect your CSV format, convert if needed, and train the risk model."

    def add_arguments(self, parser):
        parser.add_argument(
            "--input",
            "-i",
            required=True,
            help="Path to your dataset CSV (e.g. clinical/data/diabetes.csv).",
        )
        parser.add_argument(
            "--format",
            "-f",
            choices=["auto", "pima", "heart", "ready"],
            default="auto",
            help="Dataset format (default: auto-detect from columns).",
        )
        parser.add_argument(
            "--from-db",
            action="store_true",
            help="Also include portal patient data (hybrid training).",
        )
        parser.add_argument(
            "--algorithm",
            choices=["random_forest", "logistic_regression"],
            default="random_forest",
        )
        parser.add_argument(
            "--evaluate",
            action="store_true",
            help="Print accuracy / ROC-AUC before saving.",
        )
        parser.add_argument(
            "--model-version",
            default="custom-dataset-v1.0.0",
        )

    def handle(self, *args, **options):
        input_path = Path(options["input"]).resolve()
        if not input_path.exists():
            raise CommandError(
                f"Dataset not found: {input_path}\n"
                f"Copy your CSV to: E:\\Internship\\clinical\\data\\your_file.csv"
            )

        info = inspect_dataset(input_path)
        fmt = options["format"]
        if fmt == "auto":
            try:
                fmt = info["format"]
            except ValueError as exc:
                raise CommandError(str(exc)) from exc

        self.stdout.write(f"Dataset:  {input_path.name}")
        self.stdout.write(f"Rows:     {info['row_count']}")
        self.stdout.write(f"Columns:  {', '.join(info['headers'][:8])}{'...' if len(info['headers']) > 8 else ''}")
        self.stdout.write(f"Format:   {fmt}")

        if fmt == "ready":
            ready_path = input_path
        else:
            rows, skipped = convert_csv_to_training_rows(input_path, fmt)
            if len(rows) < 20:
                raise CommandError(
                    f"Only {len(rows)} valid rows after conversion (need ≥20). "
                    f"Try --format pima or --format heart. Skipped: {skipped}"
                )
            ready_path = Path("clinical/data/training_ready.csv")
            write_training_csv(rows, ready_path)
            pos_rate = sum(r["label"] for r in rows) / len(rows)
            self.stdout.write(self.style.SUCCESS(f"\nConverted -> {ready_path} ({len(rows)} rows, {pos_rate:.1%} positive)"))
            if skipped:
                self.stdout.write(f"  Skipped {skipped} invalid rows")

        labels = []
        import csv
        with ready_path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                labels.append(int(float(row["label"])))
        if len(set(labels)) < 2:
            raise CommandError("Dataset must have both label=0 and label=1 rows.")

        self.stdout.write("\nTraining model...\n")

        train_args = [
            "--csv", str(ready_path),
            "--label-column", "label",
            "--algorithm", options["algorithm"],
            "--model-version", options["model_version"],
        ]
        if options["from_db"]:
            train_args.append("--from-db")
        if options["evaluate"]:
            train_args.append("--evaluate")

        call_command("train_risk_model", *train_args)

        self.stdout.write(self.style.SUCCESS(
            "\nDone! Restart the Django server so the dashboard loads the new model:\n"
            "  python manage.py runserver"
        ))
