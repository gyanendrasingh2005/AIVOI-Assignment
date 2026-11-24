"""
PharmaRCA Model Registry
=======================
Imports and re-exports all domain models ensuring unified DeclarativeBase metadata registration.
"""

from app.database.base import Base
from app.models.enums import (
    RoleName,
    InvestigationStatus,
    PriorityLevel,
    RiskLevel,
    DocumentProcessingStatus,
    EvidenceType,
    EvidenceVerificationStatus,
    RCAMethod,
    RCAStatus,
    RootCauseCategory,
    EvidenceStrength,
    RootCauseStatus,
    ContributingFactorStatus,
    EvidenceGapPriority,
    EvidenceGapStatus,
    CAPAType,
    CAPAStatus,
    CAPATaskStatus,
    EffectivenessStatus,
    ApprovalStatus,
    AuditAction,
    AIExecutionStatus,
    ExtractionStatus,
    ExtractionReviewStatus,
    FieldExtractionStatus,
    FieldReviewDecision,
    RiskClassification,
    RiskLikelihood,
    RiskDetectability,
    InvestigationUrgency,
    RiskAssessmentStatus,
    RiskAssessmentReviewStatus,
    CauseStatus,
    CauseClassification,
    Fishbone6MCategory,
    GapCategory,
    GapDetectionType,
    CompletenessDimensionStatus,
    CompletenessOverallStatus,
)
from app.models.user import User, Role, UserRole
from app.models.investigation import Investigation, InvestigationCounter
from app.models.incident import Incident
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.rca import (
    RCAAnalysis,
    RootCause,
    ContributingFactor,
    WhyAnalysisStep,
    FishboneCategory,
    FishboneCause,
)
from app.models.evidence_gap import EvidenceGap
from app.models.completeness import CompletenessAssessment
from app.models.capa import CAPA, CAPATask, EffectivenessCheck
from app.models.approval import Approval
from app.models.audit import AuditLog
from app.models.token import RefreshToken
from app.models.ai_execution import AIExecution
from app.models.incident_extraction import IncidentExtraction
from app.models.risk_assessment import RiskAssessment

__all__ = [
    # Enums
    "RoleName",
    "InvestigationStatus",
    "PriorityLevel",
    "RiskLevel",
    "DocumentProcessingStatus",
    "EvidenceType",
    "EvidenceVerificationStatus",
    "RCAMethod",
    "RCAStatus",
    "RootCauseCategory",
    "EvidenceStrength",
    "RootCauseStatus",
    "ContributingFactorStatus",
    "EvidenceGapPriority",
    "EvidenceGapStatus",
    "CAPAType",
    "CAPAStatus",
    "CAPATaskStatus",
    "EffectivenessStatus",
    "ApprovalStatus",
    "AuditAction",
    "AIExecutionStatus",
    "ExtractionStatus",
    "ExtractionReviewStatus",
    "FieldExtractionStatus",
    "FieldReviewDecision",
    "RiskClassification",
    "RiskLikelihood",
    "RiskDetectability",
    "InvestigationUrgency",
    "RiskAssessmentStatus",
    "RiskAssessmentReviewStatus",
    "CauseStatus",
    "CauseClassification",
    "Fishbone6MCategory",
    "GapCategory",
    "GapDetectionType",
    "CompletenessDimensionStatus",
    "CompletenessOverallStatus",
    # Models
    "User",
    "Role",
    "UserRole",
    "Investigation",
    "InvestigationCounter",
    "Incident",
    "Document",
    "Evidence",
    "RCAAnalysis",
    "RootCause",
    "ContributingFactor",
    "WhyAnalysisStep",
    "FishboneCategory",
    "FishboneCause",
    "EvidenceGap",
    "CompletenessAssessment",
    "CAPA",
    "CAPATask",
    "EffectivenessCheck",
    "Approval",
    "AuditLog",
    "RefreshToken",
    "AIExecution",
    "IncidentExtraction",
    "RiskAssessment",
]
