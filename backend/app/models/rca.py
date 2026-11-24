from typing import List, Optional
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import (
    RCAMethod,
    RCAStatus,
    RootCauseCategory,
    EvidenceStrength,
    RootCauseStatus,
    ContributingFactorStatus,
)


class RCAAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Container for Root Cause Analysis investigation methodologies (5 Whys and Fishbone)."""

    __tablename__ = "rca_analyses"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_method: Mapped[str] = mapped_column(
        String(50),
        default=RCAMethod.FIVE_WHYS.value,
        nullable=False,
    )
    analysis_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default=RCAStatus.DRAFT.value,
        nullable=False,
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="rca_analyses",
    )
    creator: Mapped[Optional["User"]] = relationship("User")
    root_causes: Mapped[List["RootCause"]] = relationship(
        "RootCause",
        back_populates="rca_analysis",
        cascade="all, delete-orphan",
    )
    why_steps: Mapped[List["WhyAnalysisStep"]] = relationship(
        "WhyAnalysisStep",
        back_populates="rca_analysis",
        cascade="all, delete-orphan",
        order_by="WhyAnalysisStep.step_number",
    )
    fishbone_categories: Mapped[List["FishboneCategory"]] = relationship(
        "FishboneCategory",
        back_populates="rca_analysis",
        cascade="all, delete-orphan",
    )


class RootCause(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An identified underlying root cause contributing to the pharmaceutical incident."""

    __tablename__ = "root_causes"

    rca_analysis_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("rca_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50),
        default=RootCauseCategory.METHOD.value,
        nullable=False,
    )
    evidence_strength: Mapped[str] = mapped_column(
        String(30),
        default=EvidenceStrength.MODERATE.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default=RootCauseStatus.IDENTIFIED.value,
        nullable=False,
    )
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    human_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    rca_analysis: Mapped["RCAAnalysis"] = relationship(
        "RCAAnalysis",
        back_populates="root_causes",
    )
    contributing_factors: Mapped[List["ContributingFactor"]] = relationship(
        "ContributingFactor",
        back_populates="root_cause",
        cascade="all, delete-orphan",
    )
    evidence_gaps: Mapped[List["EvidenceGap"]] = relationship(
        "EvidenceGap",
        back_populates="root_cause",
    )
    capas: Mapped[List["CAPA"]] = relationship(
        "CAPA",
        back_populates="root_cause",
    )


class ContributingFactor(Base, UUIDPrimaryKeyMixin):
    """Contributing factor or secondary element leading up to the identified root cause."""

    __tablename__ = "contributing_factors"

    root_cause_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("root_causes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default=ContributingFactorStatus.ACTIVE.value,
        nullable=False,
    )

    root_cause: Mapped["RootCause"] = relationship(
        "RootCause",
        back_populates="contributing_factors",
    )


class WhyAnalysisStep(Base, UUIDPrimaryKeyMixin):
    """Step in a 5 Whys iterative causal inquiry grounded in manufacturing evidence."""

    __tablename__ = "why_analysis_steps"

    rca_analysis_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("rca_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_root_cause: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    rca_analysis: Mapped["RCAAnalysis"] = relationship(
        "RCAAnalysis",
        back_populates="why_steps",
    )


class FishboneCategory(Base, UUIDPrimaryKeyMixin):
    """Ishikawa 6M branch (Man, Machine, Material, Method, Measurement, Environment)."""

    __tablename__ = "fishbone_categories"

    rca_analysis_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("rca_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    rca_analysis: Mapped["RCAAnalysis"] = relationship(
        "RCAAnalysis",
        back_populates="fishbone_categories",
    )
    causes: Mapped[List["FishboneCause"]] = relationship(
        "FishboneCause",
        back_populates="category",
        cascade="all, delete-orphan",
    )


class FishboneCause(Base, UUIDPrimaryKeyMixin):
    """Specific cause node attached to a Fishbone category branch with potential hierarchical nesting."""

    __tablename__ = "fishbone_causes"

    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fishbone_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_cause_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("fishbone_causes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    cause_description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_significant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    category: Mapped["FishboneCategory"] = relationship(
        "FishboneCategory",
        back_populates="causes",
    )
    sub_causes: Mapped[List["FishboneCause"]] = relationship(
        "FishboneCause",
        backref="parent_cause",
        remote_side="FishboneCause.id",
    )
