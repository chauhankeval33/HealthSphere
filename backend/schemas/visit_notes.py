from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class VisitNoteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    visit_date: date
    doctor: Optional[str] = Field(default=None, max_length=150)
    body: str = Field(min_length=1)


class VisitNoteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    visit_date: Optional[date] = None
    doctor: Optional[str] = Field(default=None, max_length=150)
    body: Optional[str] = Field(default=None, min_length=1)