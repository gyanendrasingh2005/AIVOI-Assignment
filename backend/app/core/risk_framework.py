"""
Risk Framework Engine for Pharmaceutical Quality and Risk Assessment.
Aligns with ICH Q9 Quality Risk Management principles.
Configurable, versioned, transparent, and explainable.
"""

from typing import Dict, Any, Optional
from app.models.enums import (
    RiskClassification,
    RiskLikelihood,
    RiskDetectability,
    InvestigationUrgency,
)


class RiskFramework:
    """
    Quality Risk Framework (v1.0.0).
    Decouples risk matrix calculations from database logic.
    Provides clear explainability for calculated risk levels and urgency recommendations.
    """

    VERSION = "1.0.0"

    # Severity weights / rank
    SEVERITY_ORDER = {
        RiskClassification.CRITICAL: 4,
        RiskClassification.HIGH: 3,
        RiskClassification.MEDIUM: 2,
        RiskClassification.LOW: 1,
        RiskClassification.UNDETERMINED: 0,
    }

    # Likelihood weights / rank
    LIKELIHOOD_ORDER = {
        RiskLikelihood.HIGH: 3,
        RiskLikelihood.MEDIUM: 2,
        RiskLikelihood.LOW: 1,
        RiskLikelihood.UNDETERMINED: 0,
    }

    @classmethod
    def calculate_overall_risk(
        cls,
        severity: RiskClassification,
        likelihood: RiskLikelihood,
        detectability: Optional[RiskDetectability] = None,
    ) -> RiskClassification:
        """
        Calculate overall risk classification based on Severity, Likelihood, and optional Detectability.
        """
        if severity == RiskClassification.UNDETERMINED or likelihood == RiskLikelihood.UNDETERMINED:
            return RiskClassification.UNDETERMINED

        if severity == RiskClassification.CRITICAL:
            if likelihood in (RiskLikelihood.HIGH, RiskLikelihood.MEDIUM):
                return RiskClassification.CRITICAL
            return RiskClassification.HIGH

        if severity == RiskClassification.HIGH:
            if likelihood == RiskLikelihood.HIGH:
                return RiskClassification.HIGH
            elif likelihood == RiskLikelihood.MEDIUM:
                if detectability == RiskDetectability.LOW:
                    return RiskClassification.HIGH
                return RiskClassification.MEDIUM
            else:
                return RiskClassification.MEDIUM

        if severity == RiskClassification.MEDIUM:
            if likelihood == RiskLikelihood.HIGH:
                return RiskClassification.MEDIUM
            return RiskClassification.LOW

        if severity == RiskClassification.LOW:
            return RiskClassification.LOW

        return RiskClassification.UNDETERMINED

    @classmethod
    def determine_urgency(
        cls,
        overall_risk: RiskClassification,
        has_critical_gaps: bool = False,
        patient_impact_undetermined: bool = False,
    ) -> InvestigationUrgency:
        """
        Derive investigation urgency recommendation.
        If patient impact is undetermined or critical gaps exist, prioritize obtaining information.
        """
        if patient_impact_undetermined or has_critical_gaps:
            if overall_risk == RiskClassification.CRITICAL:
                return InvestigationUrgency.IMMEDIATE
            return InvestigationUrgency.INFO_REQUIRED

        if overall_risk == RiskClassification.CRITICAL:
            return InvestigationUrgency.IMMEDIATE
        elif overall_risk == RiskClassification.HIGH:
            return InvestigationUrgency.URGENT
        elif overall_risk in (RiskClassification.MEDIUM, RiskClassification.LOW):
            return InvestigationUrgency.STANDARD
        else:
            return InvestigationUrgency.INFO_REQUIRED

    @classmethod
    def get_matrix_metadata(cls) -> Dict[str, Any]:
        """Return metadata regarding the current risk framework rules."""
        return {
            "framework_version": cls.VERSION,
            "standard": "ICH Q9 Quality Risk Management",
            "dimensions": [
                "Product Quality Impact",
                "Patient Impact",
                "Batch & Material Impact",
                "Process Impact",
                "Equipment Impact",
                "Data Integrity Concerns",
            ],
            "severity_levels": [e.value for e in RiskClassification],
            "likelihood_levels": [e.value for e in RiskLikelihood],
            "detectability_levels": [e.value for e in RiskDetectability],
            "urgency_levels": [e.value for e in InvestigationUrgency],
        }
