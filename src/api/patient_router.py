"""Patient management API router with pagination, search, CRUD, and RBAC."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import User
from src.services.patient_service import PatientService
from src.api.dependencies import (
    require_any_authenticated,
    require_clinical_or_admin,
    require_admin,
)

router = APIRouter(prefix="/patients", tags=["Patients"])


class PatientBase(BaseModel):
    patient_nbr: int
    race: str = "Unknown"
    gender: str = "Unknown"
    age_bracket: str = "[50-60)"


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    race: Optional[str] = None
    gender: Optional[str] = None
    age_bracket: Optional[str] = None


class PatientResponse(PatientBase):
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPatients(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[PatientResponse]


@router.get("", response_model=PaginatedPatients)
def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    race: Optional[str] = None,
    gender: Optional[str] = None,
    age_bracket: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Retrieve paginated patients with multi-field search and demographic filtering."""
    skip = (page - 1) * page_size
    items, total = PatientService.get_patients(
        db=db,
        skip=skip,
        limit=page_size,
        search=search,
        race=race,
        gender=gender,
        age_bracket=age_bracket,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@router.get("/{patient_nbr}", response_model=PatientResponse)
def get_patient(
    patient_nbr: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_any_authenticated),
):
    """Fetch single patient record by ID."""
    patient = PatientService.get_patient_by_id(db, patient_nbr)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_nbr} not found",
        )
    return patient


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_clinical_or_admin),
):
    """Create a new patient record (Clinical Operations or Admin required)."""
    existing = PatientService.get_patient_by_id(db, payload.patient_nbr)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Patient {payload.patient_nbr} already exists",
        )
    patient = PatientService.create_patient(
        db=db,
        patient_data=payload.model_dump(),
        username=user.username,
        user_id=user.id,
    )
    return patient


@router.put("/{patient_nbr}", response_model=PatientResponse)
def update_patient(
    patient_nbr: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_clinical_or_admin),
):
    """Update patient demographic fields (Clinical Operations or Admin required)."""
    patient = PatientService.update_patient(
        db=db,
        patient_nbr=patient_nbr,
        update_data=payload.model_dump(exclude_unset=True),
        username=user.username,
        user_id=user.id,
    )
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_nbr} not found",
        )
    return patient


@router.delete("/{patient_nbr}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_nbr: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Delete patient and related history (Administrator role strictly required)."""
    success = PatientService.delete_patient(
        db=db,
        patient_nbr=patient_nbr,
        username=user.username,
        user_id=user.id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_nbr} not found",
        )
    return None
