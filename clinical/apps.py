import logging

from django.apps import AppConfig

logger = logging.getLogger("clinical.ml")


class ClinicalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "clinical"
    verbose_name = "Clinical Health Records"

    def ready(self):
        """Warm-load ML artifacts once at process startup to avoid per-request I/O."""
        from clinical.services.ml_engine import ChronicDiseaseRiskEngine

        try:
            ChronicDiseaseRiskEngine.initialize()
            logger.info("Chronic disease risk engine initialized successfully.")
        except Exception:
            logger.exception("Failed to initialize ML engine at startup.")
