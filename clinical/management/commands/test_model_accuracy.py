"""
One-shot model accuracy test for chronic_risk_v1.joblib.

Runs three checks:
  1. Artifact integrity  – version, feature order, pipeline steps
  2. Live patient inference – runs assess_patient() on the demo patient and
     prints all features, risk score, drivers and suggestions
  3. Synthetic hold-out accuracy – generates a labelled dataset whose ground
     truth matches the training risk surface, then reports:
       • Accuracy, Precision, Recall, F1 (binary)
       • ROC-AUC
       • 5-fold cross-validated ROC-AUC

Usage:
  python manage.py test_model_accuracy
  python manage.py test_model_accuracy --username demo_patient
  python manage.py test_model_accuracy --samples 2000
"""
from __future__ import annotations

import time

import joblib
import numpy as np
from django.core.management.base import BaseCommand, CommandError
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_score

from clinical.models import PatientUser
from clinical.services.ml_engine import ChronicDiseaseRiskEngine


class Command(BaseCommand):
    help = "One-shot accuracy check for the chronic disease risk model."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="demo_patient",
            help="Patient username to run live inference on.",
        )
        parser.add_argument(
            "--samples",
            type=int,
            default=1000,
            help="Number of synthetic hold-out samples to generate (default: 1000).",
        )

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        sep = "=" * 62

        # ── 1. Artifact integrity check ────────────────────────────────
        self.stdout.write(f"\n{sep}")
        self.stdout.write("  CHECK 1 — Artifact integrity")
        self.stdout.write(sep)

        model_path = ChronicDiseaseRiskEngine.model_path()
        if not model_path.exists():
            raise CommandError(f"Model file not found: {model_path}")

        artifact = joblib.load(model_path)
        required_keys = {"pipeline", "version", "feature_order"}
        missing = required_keys - artifact.keys()
        if missing:
            raise CommandError(f"Artifact missing keys: {missing}")

        pipeline   = artifact["pipeline"]
        version    = artifact["version"]
        feat_order = artifact["feature_order"]

        self.stdout.write(f"  Path        : {model_path}")
        self.stdout.write(f"  Version     : {version}")
        self.stdout.write(f"  Algorithm   : {type(pipeline.named_steps.get('classifier', '')).__name__}")
        self.stdout.write(f"  Features    : {len(feat_order)}")
        self.stdout.write(f"  Steps       : {list(pipeline.named_steps.keys())}")
        self.stdout.write(self.style.SUCCESS("  PASS — artifact loaded and validated\n"))

        # ── 2. Live patient inference ──────────────────────────────────
        self.stdout.write(f"{sep}")
        self.stdout.write("  CHECK 2 — Live patient inference")
        self.stdout.write(sep)

        try:
            user = PatientUser.objects.get(username=options["username"])
        except PatientUser.DoesNotExist:
            raise CommandError(
                f"Patient '{options['username']}' not found. "
                "Run: python manage.py seed_sample_data"
            )

        ChronicDiseaseRiskEngine.initialize()

        t0 = time.perf_counter()
        result = ChronicDiseaseRiskEngine.assess_patient(user)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        self.stdout.write(f"  Patient     : {options['username']} (id={user.id})")
        self.stdout.write(f"  Inference   : {elapsed_ms:.1f} ms")
        self.stdout.write(f"  Model ver.  : {result.model_version}")
        self.stdout.write(
            f"  Risk score  : {result.risk_probability:.4f}  "
            f"({result.risk_probability * 100:.1f}%)  ->  [{result.risk_label.upper()}]"
        )

        self.stdout.write("\n  -- Feature vector --")
        for feat, val in result.features.items():
            flag = ""
            # Flag features with missing / defaulted data
            if "slope" in feat and val == 0.0:
                flag = "  <- defaulted (no slope data)"
            self.stdout.write(f"    {feat:<35} {val:>10.4f}{flag}")

        self.stdout.write("\n  -- Top risk drivers --")
        if result.top_risk_drivers:
            for d in result.top_risk_drivers:
                self.stdout.write(f"    [{d['impact_score']:.4f}]  {d['label']}")
        else:
            self.stdout.write("    (none identified)")

        self.stdout.write("\n  -- Preventive suggestions --")
        for tip in result.preventative_suggestions:
            self.stdout.write(f"    • {tip}")

        self.stdout.write(self.style.SUCCESS("\n  PASS — live inference completed successfully\n"))

        # ── 3. Synthetic hold-out accuracy ────────────────────────────
        self.stdout.write(f"{sep}")
        self.stdout.write("  CHECK 3 — Synthetic hold-out accuracy")
        self.stdout.write(sep)

        n = options["samples"]
        rng = np.random.default_rng(99)  # different seed from training (42)

        # Mirror the training risk surface from ChronicDiseaseRiskEngine:
        #   risk_logit = 0.9*X[:,1] + 0.7*X[:,2] + 0.6*X[:,4]
        #              + 0.8*X[:,6] + 0.5*X[:,0]
        # threshold 0.8 → ~30% positive rate
        X_hold = rng.normal(size=(n, len(feat_order)))
        logit = (
            0.9 * X_hold[:, 1]
            + 0.7 * X_hold[:, 2]
            + 0.6 * X_hold[:, 4]
            + 0.8 * X_hold[:, 6]
            + 0.5 * X_hold[:, 0]
        )
        y_hold = (logit + rng.normal(0, 0.5, size=n) > 0.8).astype(int)

        pos_rate = np.mean(y_hold)
        self.stdout.write(f"  Hold-out N  : {n}")
        self.stdout.write(f"  Positive %  : {pos_rate:.1%}  ({int(pos_rate * n)} positives)")

        t0 = time.perf_counter()
        y_pred  = pipeline.predict(X_hold)
        y_proba = pipeline.predict_proba(X_hold)[:, 1]
        pred_ms = (time.perf_counter() - t0) * 1000

        acc       = accuracy_score(y_hold, y_pred)
        prec      = precision_score(y_hold, y_pred, zero_division=0)
        rec       = recall_score(y_hold, y_pred, zero_division=0)
        f1        = f1_score(y_hold, y_pred, zero_division=0)
        roc_auc   = roc_auc_score(y_hold, y_proba)

        self.stdout.write(f"\n  -- Hold-out metrics --")
        self.stdout.write(f"    Accuracy   : {acc:.4f}  ({acc*100:.1f}%)")
        self.stdout.write(f"    Precision  : {prec:.4f}")
        self.stdout.write(f"    Recall     : {rec:.4f}")
        self.stdout.write(f"    F1 Score   : {f1:.4f}")
        self.stdout.write(f"    ROC-AUC    : {roc_auc:.4f}")
        self.stdout.write(f"    Batch infer: {pred_ms:.1f} ms for {n} samples")

        self.stdout.write(f"\n  -- Classification report --")
        report = classification_report(y_hold, y_pred, digits=3, target_names=["Low risk", "High risk"])
        for line in report.splitlines():
            self.stdout.write(f"    {line}")

        # 5-fold cross-validation on hold-out set (pipeline already fitted)
        self.stdout.write(f"\n  -- 5-fold cross-validated ROC-AUC (on synthetic set) --")
        cv_scores = cross_val_score(pipeline, X_hold, y_hold, cv=5, scoring="roc_auc", n_jobs=-1)
        self.stdout.write(
            f"    {' | '.join(f'{s:.3f}' for s in cv_scores)}"
        )
        self.stdout.write(f"    Mean: {cv_scores.mean():.4f}  ±  {cv_scores.std():.4f}")

        # Overall verdict
        self.stdout.write(f"\n  -- Overall verdict --")
        if roc_auc >= 0.85:
            verdict = self.style.SUCCESS(f"EXCELLENT  (ROC-AUC {roc_auc:.3f} ≥ 0.85)")
        elif roc_auc >= 0.70:
            verdict = self.style.WARNING(f"ACCEPTABLE (ROC-AUC {roc_auc:.3f} ≥ 0.70)")
        else:
            verdict = self.style.ERROR(f"POOR       (ROC-AUC {roc_auc:.3f} < 0.70 — consider retraining)")

        self.stdout.write(f"    {verdict}")
        self.stdout.write(f"\n{sep}\n")
