from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import (
    RCAMethod,
    RCAStatus,
    RootCauseCategory,
    EvidenceStrength,
    RootCauseStatus,
    ContributingFactorStatus,
)


class WhyAnalysisStepBase(BaseModel):
    step_number: int = Field(..., ge=1)
    question: str = Field(..., max_length=500)
    answer: str
    evidence_reference: Optional[str] = Field(None, max_length=255)
    is_root_cause: bool = False


class WhyAnalysisStepCreate(WhyAnalysisStepBase):
    pass


class WhyAnalysisStepResponse(WhyAnalysisStepBase):
    id: str
    rca_analysis_id: str

    model_config = ConfigDict(from_attributes=True)


class FishboneCauseBase(BaseModel):
    cause_description: str
    parent_cause_id: Optional[str] = None
    evidence_reference: Optional[str] = Field(None, max_length=255)
    is_significant: bool = False


class FishboneCauseCreate(FishboneCauseBase):
    pass


class FishboneCauseResponse(FishboneCauseBase):
    id: str
    category_id: str

    model_config = ConfigDict(from_attributes=True)


class FishboneCategoryResponse(BaseModel):
    id: str
    rca_analysis_id: str
    name: str
    causes: List[FishboneCauseResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ContributingFactorBase(BaseModel):
    description: str
    category: str = Field(..., max_length=50)
    evidence_reference: Optional[str] = Field(None, max_length=255)
    status: ContributingFactorStatus = ContributingFactorStatus.ACTIVE


class ContributingFactorCreate(ContributingFactorBase):
    pass


class ContributingFactorResponse(ContributingFactorBase):
    id: str
    root_cause_id: str

    model_config = ConfigDict(from_attributes=True)


class RootCauseBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    category: RootCauseCategory = RootCauseCategory.METHOD
    evidence_strength: EvidenceStrength = EvidenceStrength.MODERATE
    status: RootCauseStatus = RootCauseStatus.IDENTIFIED
    ai_generated: bool = False
    human_confirmed: bool = False


class RootCauseCreate(RootCauseBase):
    pass


class RootCauseResponse(RootCauseBase):
    id: str
    rca_analysis_id: str
    created_at: datetime
    updated_at: datetime
    contributing_factors: List[ContributingFactorResponse] = []

    model_config = ConfigDict(from_attributes=True)


class RCAAnalysisBase(BaseModel):
    analysis_method: RCAMethod = RCAMethod.FIVE_WHYS
    analysis_version: int = 1
    summary: Optional[str] = None
    status: RCAStatus = RCAStatus.DRAFT


class RCAAnalysisCreate(RCAAnalysisBase):
    investigation_id: str


class RCAAnalysisResponse(RCAAnalysisBase):
    id: str
    investigation_id: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    root_causes: List[RootCauseResponse] = []
    why_steps: List[WhyAnalysisStepResponse] = []
    fishbone_categories: List[FishboneCategoryResponse] = []

    model_config = ConfigDict(from_attributes=True)
