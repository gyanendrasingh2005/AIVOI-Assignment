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
from app.models.capa import CAPA, CAPATask, EffectivenessCheck
from app.models.approval import Approval
from app.models.audit import AuditLog
from app.models.token import RefreshToken

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
    "CAPA",
    "CAPATask",
    "EffectivenessCheck",
    "Approval",
    "AuditLog",
    "RefreshToken",
]
