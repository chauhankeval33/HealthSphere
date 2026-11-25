
from datetime import date
from pydantic import BaseModel, Field
from typing import Optional


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    blood_group: Optional[str] = None

    allergies: list[str] = Field(default_factory=list)
    medical_conditions: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class PatientUpdate(BaseModel):
    full_name: Optional[str] = Field(
        default=None, min_length=2, max_length=120
    )
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    blood_group: Optional[str] = None

    allergies: Optional[list[str]] = None
    medical_conditions: Optional[list[str]] = None
    notes: Optional[str] = None
