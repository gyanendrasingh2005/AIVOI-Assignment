from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.enums import DocumentProcessingStatus


class DocumentBase(BaseModel):
    original_filename: str = Field(..., max_length=255)
    file_type: str = Field(..., max_length=100)
    file_size: int = Field(..., ge=0)


class DocumentCreate(DocumentBase):
    investigation_id: str
    stored_filename: str = Field(..., max_length=255)
    storage_path: str = Field(..., max_length=500)
    checksum: str = Field(default="", max_length=64)
    file_extension: Optional[str] = Field(None, max_length=20)
    document_category: Optional[str] = Field(None, max_length=50)
    extracted_text: Optional[str] = None
    extracted_at: Optional[datetime] = None
    extraction_error: Optional[str] = None
    page_count: Optional[int] = None
    character_count: Optional[int] = None
    source_type: str = "file_upload"
    metadata_json: Optional[Dict[str, Any]] = None
    uploaded_by: Optional[str] = None
    processing_status: DocumentProcessingStatus = DocumentProcessingStatus.PENDING


class DocumentTextIngestRequest(BaseModel):
    source_type: Literal["pasted_text", "email"] = "pasted_text"
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    subject: Optional[str] = Field(None, max_length=255)
    sender: Optional[str] = Field(None, max_length=255)
    received_date: Optional[datetime] = None
    document_category: Optional[str] = Field(None, max_length=50)

    @field_validator("body")
    def validate_body_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Body content cannot be empty or purely whitespace.")
        return v


class DocumentListItem(BaseModel):
    id: str
    investigation_id: str
    original_filename: str
    file_type: str
    file_size: int
    checksum: str
    file_extension: Optional[str] = None
    document_category: Optional[str] = None
    processing_status: str
    source_type: str
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    page_count: Optional[int] = None
    character_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    items: List[DocumentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentResponse(DocumentBase):
    id: str
    investigation_id: str
    stored_filename: str
    checksum: str
    file_extension: Optional[str] = None
    document_category: Optional[str] = None
    processing_status: str
    source_type: str
    page_count: Optional[int] = None
    character_count: Optional[int] = None
    extracted_at: Optional[datetime] = None
    extraction_error: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    is_archived: bool = False

    model_config = ConfigDict(from_attributes=True)


class DocumentPageItem(BaseModel):
    page_number: int
    text: str
    character_count: int
    word_count: int


class DocumentExtractedTextResponse(BaseModel):
    document_id: str
    investigation_id: str
    original_filename: str
    processing_status: str
    page_count: Optional[int] = None
    character_count: Optional[int] = None
    extracted_text: Optional[str] = None
    extracted_at: Optional[datetime] = None
    pages: List[DocumentPageItem] = []
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExtractionTriggerResponse(BaseModel):
    document_id: str
    status: str
    page_count: Optional[int] = None
    extracted_character_count: Optional[int] = None
    message: str
    error_message: Optional[str] = None
