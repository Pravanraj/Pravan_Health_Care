"""Patient domain service managing CRUD operations, searching, and audit tracking."""

from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.database.models import Patient, Encounter
from src.utils.logger import log_audit_event


class PatientService:
    """Service handling patient queries and mutations with full audit compliance."""

    @staticmethod
    def get_patients(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        race: Optional[str] = None,
        gender: Optional[str] = None,
        age_bracket: Optional[str] = None,
    ) -> Tuple[List[Patient], int]:
        """Retrieve paginated patients with optional filtering and search."""
        query = db.query(Patient)

        if search:
            search_term = f"%{search}%"
            # If search is integer, also match patient_nbr directly
            if search.isdigit():
                query = query.filter(
                    or_(
                        Patient.patient_nbr == int(search),
                        Patient.race.ilike(search_term),
                        Patient.gender.ilike(search_term),
                    )
                )
            else:
                query = query.filter(
                    or_(
                        Patient.race.ilike(search_term),
                        Patient.gender.ilike(search_term),
                        Patient.age_bracket.ilike(search_term),
                    )
                )

        if race and race != "All":
            query = query.filter(Patient.race == race)
        if gender and gender != "All":
            query = query.filter(Patient.gender == gender)
        if age_bracket and age_bracket != "All":
            query = query.filter(Patient.age_bracket == age_bracket)

        total = query.count()
        patients = query.order_by(Patient.patient_nbr).offset(skip).limit(limit).all()
        return patients, total

    @staticmethod
    def get_patient_by_id(db: Session, patient_nbr: int) -> Optional[Patient]:
        """Fetch a single patient record by identifier."""
        return db.query(Patient).filter(Patient.patient_nbr == patient_nbr).first()

    @staticmethod
    def create_patient(
        db: Session,
        patient_data: Dict[str, Any],
        username: str = "system",
        user_id: Optional[int] = None,
    ) -> Patient:
        """Create a new patient record and write to audit trail."""
        patient = Patient(
            patient_nbr=patient_data["patient_nbr"],
            race=patient_data.get("race", "Unknown"),
            gender=patient_data.get("gender", "Unknown"),
            age_bracket=patient_data.get("age_bracket", "[50-60)"),
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

        log_audit_event(
            db=db,
            username=username,
            action="CREATE",
            entity_name="patient",
            entity_id=str(patient.patient_nbr),
            details={"race": patient.race, "gender": patient.gender, "age_bracket": patient.age_bracket},
            user_id=user_id,
        )
        return patient

    @staticmethod
    def update_patient(
        db: Session,
        patient_nbr: int,
        update_data: Dict[str, Any],
        username: str = "system",
        user_id: Optional[int] = None,
    ) -> Optional[Patient]:
        """Update an existing patient record and record diffs in audit trail."""
        patient = db.query(Patient).filter(Patient.patient_nbr == patient_nbr).first()
        if not patient:
            return None

        diffs = {}
        for key in ["race", "gender", "age_bracket"]:
            if key in update_data and update_data[key] is not None:
                old_val = getattr(patient, key)
                new_val = update_data[key]
                if old_val != new_val:
                    diffs[key] = {"old": old_val, "new": new_val}
                    setattr(patient, key, new_val)

        if diffs:
            db.commit()
            db.refresh(patient)
            log_audit_event(
                db=db,
                username=username,
                action="UPDATE",
                entity_name="patient",
                entity_id=str(patient_nbr),
                details=diffs,
                user_id=user_id,
            )

        return patient

    @staticmethod
    def delete_patient(
        db: Session,
        patient_nbr: int,
        username: str = "system",
        user_id: Optional[int] = None,
    ) -> bool:
        """Delete patient and associated cascades, logging deletion."""
        patient = db.query(Patient).filter(Patient.patient_nbr == patient_nbr).first()
        if not patient:
            return False

        db.delete(patient)
        db.commit()

        log_audit_event(
            db=db,
            username=username,
            action="DELETE",
            entity_name="patient",
            entity_id=str(patient_nbr),
            details={"deleted": True},
            user_id=user_id,
        )
        return True
