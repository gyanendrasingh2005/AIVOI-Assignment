from app.repositories.base import BaseRepository
from app.repositories.user_repository import (
    UserRepository,
    RoleRepository,
    user_repo,
    role_repo,
)
from app.repositories.investigation_repository import (
    InvestigationRepository,
    IncidentRepository,
    investigation_repo,
    incident_repo,
)
from app.repositories.document_evidence_repository import (
    DocumentRepository,
    EvidenceRepository,
    document_repo,
    evidence_repo,
)
from app.repositories.rca_repository import (
    RCARepository,
    EvidenceGapRepository,
    rca_repo,
    evidence_gap_repo,
)
from app.repositories.capa_repository import (
    CAPARepository,
    capa_repo,
)
from app.repositories.approval_audit_repository import (
    ApprovalRepository,
    AuditLogRepository,
    approval_repo,
    audit_repo,
)

__all__ = [
    "BaseRepository",
    "UserRepository",
    "RoleRepository",
    "user_repo",
    "role_repo",
    "InvestigationRepository",
    "IncidentRepository",
    "investigation_repo",
    "incident_repo",
    "DocumentRepository",
    "EvidenceRepository",
    "document_repo",
    "evidence_repo",
    "RCARepository",
    "EvidenceGapRepository",
    "rca_repo",
    "evidence_gap_repo",
    "CAPARepository",
    "capa_repo",
    "ApprovalRepository",
    "AuditLogRepository",
    "approval_repo",
    "audit_repo",
]
