from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import DocumentProcessingStatus


class DocumentBase(BaseModel):
    original_filename: str = Field(..., max_length=255)
    file_type: str = Field(..., max_length=100)
    file_size: int = Field(..., gt=0)


class DocumentCreate(DocumentBase):
    investigation_id: str
    stored_filename: str = Field(..., max_length=255)
    storage_path: str = Field(..., max_length=500)
    extracted_text: Optional[str] = None
    processing_status: DocumentProcessingStatus = DocumentProcessingStatus.PENDING


class DocumentResponse(DocumentBase):
    id: str
    investigation_id: str
    stored_filename: str
    extracted_text: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    processing_status: str

    model_config = ConfigDict(from_attributes=True)
