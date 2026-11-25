from pydantic import BaseModel
from typing import Optional


class DocumentResponse(BaseModel):
    id: str
    patient_id: str
    file_name: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    processing_status: str
    created_at: Optional[str] = None