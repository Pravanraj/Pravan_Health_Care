"""Encounter API router providing multi-parameter search, sorting, and CRUD."""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import User
from src.services.encounter_service import EncounterService
from src.api.dependencies import (
    require_any_authenticated,
    require_clinical_or_admin,
    require_admin,
)

router = APIRouter(prefix="/encounters", tags=["Encounters"])


class EncounterCreatePayload(BaseModel):
    encounter_id: int
    patient_nbr: int
    admission_type_id: int = 1
    discharge_disposition_id: int = 1
    admission_source_id: int = 1
    time_in_hospital: int = 1
    payer_code: Optional[str] = "Unknown"
    medical_specialty: Optional[str] = "Unknown"
    num_lab_procedures: int = 0
    num_procedures: int = 0
    num_medications: int = 0
    number_diagnoses: int = 1
    readmitted_raw: str = "NO"


class EncounterUpdatePayload(BaseModel):
    admission_type_id: Optional[int] = None
    discharge_disposition_id: Optional[int] = None
    admission_source_id: Optional[int] = None
    time_in_hospital: Optional[int] = None
    medical_specialty: Optional[str] = None
    num_medications: Optional[int] = None
    num_lab_procedures: Optional[int] = None


class DiagnosisItem(BaseModel):
    diag_seq: int
    icd9_code: str
    category_name: str
    model_config = ConfigDict(from_attributes=True)


class OutcomeItem(BaseModel):
    readmitted_raw: str
    readmitted_30d: bool
    is_mortality: bool
    model_config = ConfigDict(from_attributes=True)


class EncounterItemResponse(BaseModel):
    encounter_id: int
    patient_nbr: int
    admission_type_id: int
    discharge_disposition_id: int
    admission_date: date
    discharge_date: date
    time_in_hospital: int
    medical_specialty: Optional[str]
    num_medications: int
    num_lab_procedures: int
    outcome: Optional[OutcomeItem] = None
    diagnoses: List[DiagnosisItem] = []
    model_config = ConfigDict(from_attributes=True)


class PaginatedEncounters(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[EncounterItemResponse]


@router.get("", response_model=PaginatedEncounters)
def list_encounters(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    patient_nbr: Optional[int] = None,
    admission_type_id: Optional[int] = None,
    readmitted: Optional[str] = None,
    min_los: Optional[int] = None,
    max_los: Optional[int] = None,
    medical_specialty: Optional[str] = None,
    diag_category: Optional[str] = None,
    sort_by: str = Query("admission_date", enum=["admission_date", "time_in_hospital", "encounter_id"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Search and filter clinical encounters with sorting and pagination."""
    skip = (page - 1) * page_size
    items, total = EncounterService.get_encounters(
        db=db,
        skip=skip,
        limit=page_size,
        patient_nbr=patient_nbr,
        admission_type_id=admission_type_id,
        readmitted=readmitted,
        min_los=min_los,
        max_los=max_los,
        medical_specialty=medical_specialty,
        diag_category=diag_category,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/{encounter_id}", response_model=EncounterItemResponse)
def get_encounter(
    encounter_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Fetch complete encounter record with clinical outcomes and diagnoses."""
    enc = EncounterService.get_encounter_by_id(db, encounter_id)
    if not enc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encounter {encounter_id} not found",
        )
    return enc


@router.post("", response_model=EncounterItemResponse, status_code=status.HTTP_201_CREATED)
def create_encounter(
    payload: EncounterCreatePayload,
    db: Session = Depends(get_db),
    user: User = Depends(require_clinical_or_admin),
):
    """Create new clinical encounter record."""
    existing = EncounterService.get_encounter_by_id(db, payload.encounter_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Encounter {payload.encounter_id} already exists",
        )
    enc = EncounterService.create_encounter(
        db=db,
        data=payload.model_dump(),
        username=user.username,
        user_id=user.id,
    )
    return enc


@router.put("/{encounter_id}", response_model=EncounterItemResponse)
def update_encounter(
    encounter_id: int,
    payload: EncounterUpdatePayload,
    db: Session = Depends(get_db),
    user: User = Depends(require_clinical_or_admin),
):
    """Update encounter fields (LOS, specialty, medication count)."""
    enc = EncounterService.update_encounter(
        db=db,
        encounter_id=encounter_id,
        update_data=payload.model_dump(exclude_unset=True),
        username=user.username,
        user_id=user.id,
    )
    if not enc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encounter {encounter_id} not found",
        )
    return enc


@router.delete("/{encounter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_encounter(
    encounter_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Delete encounter record (Administrator required)."""
    success = EncounterService.delete_encounter(
        db=db,
        encounter_id=encounter_id,
        username=user.username,
        user_id=user.id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encounter {encounter_id} not found",
        )
    return None
