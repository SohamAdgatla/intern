"""
Train the chronic disease risk classifier and persist to models/chronic_risk_v1.joblib.

Usage examples
--------------
# Train Random Forest on patients in your PostgreSQL database
python manage.py train_risk_model --from-db

# Train Logistic Regression (more interpretable coefficients)
python manage.py train_risk_model --from-db --algorithm logistic_regression

# Train from a CSV file (Kaggle-style features)
python manage.py train_risk_model --csv path/to/diabetes.csv --label-column Outcome

# Evaluate with cross-validation before saving
python manage.py train_risk_model --from-db --evaluate

# HYBRID: combine your portal patients + Kaggle CSV (recommended)
python manage.py prepare_kaggle_csv -i diabetes.csv -f pima -o clinical/data/training_ready.csv
python manage.py train_risk_model --from-db --csv clinical/data/training_ready.csv --evaluate
"""
from __future__ import annotations

import csv
from pathlib import Path

import joblib
import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from clinical.models import Condition, ConditionClinicalStatus, PatientUser
from clinical.services.ml_engine import ChronicDiseaseRiskEngine

# SNOMED / ICD codes treated as positive chronic-disease label
CHRONIC_CONDITION_CODES = {
    "44054006",   # Type 2 diabetes
    "38341003",   # Hypertension
    "13644009",   # Hypercholesterolemia
    "414545008",  # Ischemic heart disease
}


class Command(BaseCommand):
    help = "Train chronic disease risk model and save joblib artifact."

    def add_arguments(self, parser):
        parser.add_argument(
            "--from-db",
            action="store_true",
            help="Build training matrix from PatientUser observations + conditions.",
        )
        parser.add_argument(
            "--csv",
            type=str,
            help="Path to CSV with numeric feature columns + label column.",
        )
        parser.add_argument(
            "--label-column",
            type=str,
            default="label",
            help="CSV column name for binary target (0/1). Default: label",
        )
        parser.add_argument(
            "--algorithm",
            choices=["random_forest", "logistic_regression"],
            default="random_forest",
            help="Classifier algorithm (default: random_forest).",
        )
        parser.add_argument(
            "--evaluate",
            action="store_true",
            help="Run hold-out test metrics and cross-validation before saving.",
        )
        parser.add_argument(
            "--model-version",
            type=str,
            default="trained-v1.0.0",
            help="Version string stored in the artifact metadata.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Output path (default: models/chronic_risk_v1.joblib).",
        )

    def handle(self, *args, **options):
        if not options["from_db"] and not options["csv"]:
            raise CommandError(
                "Specify at least one data source: --from-db and/or --csv path/to/file.csv"
            )

        feature_order = list(ChronicDiseaseRiskEngine._feature_order)
        X_parts: list[np.ndarray] = []
        y_parts: list[np.ndarray] = []
        source_counts: dict[str, int] = {}

        if options["from_db"]:
            X_db, y_db, feature_order = self._build_from_database()
            X_parts.append(X_db)
            y_parts.append(y_db)
            source_counts["portal_patients"] = len(X_db)
            self.stdout.write(f"Loaded {len(X_db)} rows from portal database (real longitudinal features).")

        if options["csv"]:
            X_csv, y_csv, csv_features = self._build_from_csv(options["csv"], options["label_column"])
            if csv_features != feature_order:
                raise CommandError("CSV feature columns do not match engine feature order.")
            X_parts.append(X_csv)
            y_parts.append(y_csv)
            source_counts["kaggle_csv"] = len(X_csv)
            self.stdout.write(f"Loaded {len(X_csv)} rows from CSV (external dataset).")

        X = np.vstack(X_parts)
        y = np.concatenate(y_parts)

        if len(X) < 20:
            raise CommandError(
                f"Need at least 20 training rows; found {len(X)}. "
                "Seed more patient data or use a larger CSV."
            )

        if len(np.unique(y)) < 2:
            raise CommandError("Target column must contain both classes (0 and 1).")

        pipeline = self._build_pipeline(options["algorithm"])
        feature_order_tuple = tuple(feature_order)

        if options["evaluate"]:
            self._evaluate(pipeline, X, y)

        pipeline.fit(X, y)

        out_path = Path(options["output"]) if options["output"] else ChronicDiseaseRiskEngine.model_path()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        artifact = {
            "pipeline": pipeline,
            "version": options["model_version"],
            "feature_order": feature_order_tuple,
            "algorithm": options["algorithm"],
            "training_samples": len(X),
            "positive_rate": float(np.mean(y)),
            "source_counts": source_counts,
            "hybrid_training": len(source_counts) > 1,
        }
        joblib.dump(artifact, out_path)

        self.stdout.write(self.style.SUCCESS(f"Model saved to {out_path}"))
        self.stdout.write(f"  Algorithm:   {options['algorithm']}")
        self.stdout.write(f"  Samples:     {len(X)}")
        if source_counts:
            for source, count in source_counts.items():
                self.stdout.write(f"    - {source}: {count}")
        self.stdout.write(f"  Pos. rate:   {artifact['positive_rate']:.1%}")
        if len(source_counts) > 1:
            self.stdout.write(self.style.WARNING(
                "  Hybrid model: portal rows use real trend slopes; Kaggle rows typically use slope=0."
            ))
        self.stdout.write(f"  Version:     {options['model_version']}")
        self.stdout.write(
            "\nRestart Django (or runserver) so ChronicDiseaseRiskEngine reloads the new weights."
        )

    def _build_pipeline(self, algorithm: str) -> Pipeline:
        if algorithm == "logistic_regression":
            classifier = LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42,
            )
        else:
            classifier = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_leaf=5,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
        return Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ])

    def _build_from_database(self):
        """Feature matrix from ORM + binary label from active chronic conditions."""
        feature_order = list(ChronicDiseaseRiskEngine._feature_order)
        rows = []
        labels = []

        patients = PatientUser.objects.filter(role="patient").prefetch_related("conditions__code")
        for patient in patients:
            try:
                vector, _features, _trends = ChronicDiseaseRiskEngine.build_feature_vector(patient)
            except Exception:
                continue
            rows.append(vector[0])

            has_chronic = Condition.objects.filter(
                patient=patient,
                clinical_status=ConditionClinicalStatus.ACTIVE,
                code__code__in=CHRONIC_CONDITION_CODES,
            ).exists()
            labels.append(1 if has_chronic else 0)

        if not rows:
            raise CommandError("No patients with observation data found in database.")

        return np.array(rows, dtype=np.float64), np.array(labels, dtype=np.int32), feature_order

    def _build_from_csv(self, csv_path: str, label_column: str):
        """
        Load external dataset. CSV must contain the 11 feature columns matching
        ChronicDiseaseRiskEngine._feature_order, plus a binary label column.

        For Kaggle Pima Indians Diabetes, map columns first or use a preprocessed file.
        """
        path = Path(csv_path)
        if not path.exists():
            raise CommandError(f"CSV not found: {path}")

        feature_order = list(ChronicDiseaseRiskEngine._feature_order)
        rows = []
        labels = []

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if label_column not in row:
                    raise CommandError(f"Label column '{label_column}' missing in CSV header.")
                try:
                    features = [float(row[col]) for col in feature_order]
                    label = int(float(row[label_column]))
                except (KeyError, ValueError) as exc:
                    raise CommandError(
                        f"CSV must include columns: {feature_order} + {label_column}. Error: {exc}"
                    ) from exc
                rows.append(features)
                labels.append(label)

        return np.array(rows, dtype=np.float64), np.array(labels, dtype=np.int32), feature_order

    def _evaluate(self, pipeline: Pipeline, X: np.ndarray, y: np.ndarray) -> None:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        y_proba = pipeline.predict_proba(X_test)[:, 1]

        self.stdout.write("\n--- Hold-out evaluation (25%) ---")
        self.stdout.write(classification_report(y_test, y_pred, digits=3))
        self.stdout.write(f"ROC-AUC: {roc_auc_score(y_test, y_proba):.3f}")

        cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring="roc_auc")
        self.stdout.write(f"\n5-fold CV ROC-AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})\n")
