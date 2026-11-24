"""
PharmaRCA Database Entity Architecture Specification
====================================================
Establishes the foundational model registry for:
- User & Role
- Investigation & Incident
- Document & Evidence
- RCAAnalysis, RootCause, ContributingFactor & EvidenceGap
- CAPA & CAPATask
- Approval (21 CFR Part 11 Electronic Signature)
- AuditLog (Immutable ALCOA+ Audit Trail)
"""

from sqlalchemy import (
    String,
    Text,
    Boolean,
    Integer,
    ForeignKey,
    JSON,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List
from datetime import datetime, timezone

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    users: Mapped[List["User"]] = relationship("User", back_populates="role")


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role: Mapped["Role"] = relationship("Role", back_populates="users")
    investigations: Mapped[List["Investigation"]] = relationship(
        "Investigation", back_populates="lead_investigator", foreign_keys="Investigation.lead_investigator_id"
    )


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "incidents"

    incident_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    manufacturing_site: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_operation: Mapped[str] = mapped_column(String(100), nullable=False)
    product_name: Mapped[str] = mapped_column(String(150), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    discovery_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Investigation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "investigations"

    reference_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    incident_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="MAJOR", nullable=False)
    stage: Mapped[str] = mapped_column(String(50), default="INTAKE", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False)
    lead_investigator_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    lead_investigator: Mapped[Optional["User"]] = relationship("User", back_populates="investigations", foreign_keys=[lead_investigator_id])
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="investigation")
    rca_analyses: Mapped[List["RCAAnalysis"]] = relationship("RCAAnalysis", back_populates="investigation")
    capas: Mapped[List["CAPA"]] = relationship("CAPA", back_populates="investigation")


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "documents"

    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="documents")
    evidence_chunks: Mapped[List["Evidence"]] = relationship("Evidence", back_populates="document")


class Evidence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "evidence_chunks"

    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="evidence_chunks")


class RCAAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "rca_analyses"

    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=False)
    methodology: Mapped[str] = mapped_column(String(50), default="FIVE_WHYS", nullable=False)
    executive_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="rca_analyses")
    root_causes: Mapped[List["RootCause"]] = relationship("RootCause", back_populates="rca_analysis")
    gaps: Mapped[List["EvidenceGap"]] = relationship("EvidenceGap", back_populates="rca_analysis")


class RootCause(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "root_causes"

    rca_analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("rca_analyses.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # 6M Category
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    rca_analysis: Mapped["RCAAnalysis"] = relationship("RCAAnalysis", back_populates="root_causes")
    contributing_factors: Mapped[List["ContributingFactor"]] = relationship("ContributingFactor", back_populates="root_cause")


class ContributingFactor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "contributing_factors"

    root_cause_id: Mapped[str] = mapped_column(String(36), ForeignKey("root_causes.id"), nullable=False)
    factor_description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    root_cause: Mapped["RootCause"] = relationship("RootCause", back_populates="contributing_factors")


class EvidenceGap(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "evidence_gaps"

    rca_analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("rca_analyses.id"), nullable=False)
    gap_description: Mapped[str] = mapped_column(Text, nullable=False)
    missing_document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_implication: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="IDENTIFIED", nullable=False)

    rca_analysis: Mapped["RCAAnalysis"] = relationship("RCAAnalysis", back_populates="gaps")


class CAPA(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "capas"

    investigation_id: Mapped[str] = mapped_column(String(36), ForeignKey("investigations.id"), nullable=False)
    capa_type: Mapped[str] = mapped_column(String(50), nullable=False)  # IMMEDIATE_CONTAINMENT, CORRECTIVE, PREVENTIVE
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    assigned_to_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)

    investigation: Mapped["Investigation"] = relationship("Investigation", back_populates="capas")
    tasks: Mapped[List["CAPATask"]] = relationship("CAPATask", back_populates="capa")


class CAPATask(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "capa_tasks"

    capa_id: Mapped[str] = mapped_column(String(36), ForeignKey("capas.id"), nullable=False)
    action_step: Mapped[str] = mapped_column(Text, nullable=False)
    target_due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    capa: Mapped["CAPA"] = relationship("CAPA", back_populates="tasks")


class Approval(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "approvals"

    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    action_meaning: Mapped[str] = mapped_column(String(50), nullable=False)
    signature_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    declaration_text: Mapped[str] = mapped_column(Text, nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class AuditLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "audit_logs"

    entity_name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    performed_by_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    reason_for_change: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    record_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
