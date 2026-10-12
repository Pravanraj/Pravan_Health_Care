"""Encounter domain service managing queries, multi-filter search, sorting, and CRUD."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import date, datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, asc

from src.database.models import (
    Encounter,
    Diagnosis,
    LabResult,
    Medication,
    Outcome,
    AdmissionType,
    DischargeDisposition,
    AdmissionSource,
)
from src.utils.logger import log_audit_event


class EncounterService:
    """Service executing complex encounter searches, multi-table joins, and CRUD."""

    @staticmethod
    def get_encounters(
        db: Session,
        skip: int = 0,
        limit: int = 50,
        patient_nbr: Optional[int] = None,
        admission_type_id: Optional[int] = None,
        readmitted: Optional[str] = None,
        readmitted_30d: Optional[bool] = None,
        min_los: Optional[int] = None,
        max_los: Optional[int] = None,
        medical_specialty: Optional[str] = None,
        diag_category: Optional[str] = None,
        sort_by: str = "admission_date",
        sort_order: str = "desc",
    ) -> Tuple[List[Encounter], int]:
        """Fetch filtered and sorted encounters with eagerly loaded clinical relationships."""
        query = (
            db.query(Encounter)
            .options(
                joinedload(Encounter.patient),
                joinedload(Encounter.admission_type),
                joinedload(Encounter.discharge_disposition),
                joinedload(Encounter.outcome),
                joinedload(Encounter.diagnoses),
            )
        )

        if patient_nbr:
            query = query.filter(Encounter.patient_nbr == patient_nbr)

        if admission_type_id and admission_type_id > 0:
            query = query.filter(Encounter.admission_type_id == admission_type_id)

        if min_los is not None:
            query = query.filter(Encounter.time_in_hospital >= min_los)

        if max_los is not None:
            query = query.filter(Encounter.time_in_hospital <= max_los)

        if medical_specialty and medical_specialty != "All":
            query = query.filter(Encounter.medical_specialty.ilike(f"%{medical_specialty}%"))

        # Outcome filters
        if readmitted and readmitted != "All":
            query = query.join(Encounter.outcome).filter(Outcome.readmitted_raw == readmitted)
        elif readmitted_30d is not None:
            query = query.join(Encounter.outcome).filter(Outcome.readmitted_30d == readmitted_30d)

        # Diagnosis category filter
        if diag_category and diag_category != "All":
            query = query.join(Encounter.diagnoses).filter(Diagnosis.category_name == diag_category)

        total = query.distinct().count()

        # Sorting logic
        sort_column = getattr(Encounter, sort_by, Encounter.admission_date)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        encounters = query.offset(skip).limit(limit).all()
        return encounters, total

    @staticmethod
    def get_encounter_by_id(db: Session, encounter_id: int) -> Optional[Encounter]:
        """Fetch single encounter with all nested clinical records."""
        return (
            db.query(Encounter)
            .options(
                joinedload(Encounter.patient),
                joinedload(Encounter.admission_type),
                joinedload(Encounter.discharge_disposition),
                joinedload(Encounter.admission_source),
                joinedload(Encounter.diagnoses),
                joinedload(Encounter.lab_result),
                joinedload(Encounter.medications),
                joinedload(Encounter.outcome),
            )
            .filter(Encounter.encounter_id == encounter_id)
            .first()
        )

    @staticmethod
    def create_encounter(
        db: Session,
        data: Dict[str, Any],
        username: str = "system",
        user_id: Optional[int] = None,
    ) -> Encounter:
        """Create new clinical encounter with outcome and diagnosis."""
        enc = Encounter(
            encounter_id=data["encounter_id"],
            patient_nbr=data["patient_nbr"],
            admission_type_id=data.get("admission_type_id", 1),
            discharge_disposition_id=data.get("discharge_disposition_id", 1),
            admission_source_id=data.get("admission_source_id", 1),
            admission_date=data.get("admission_date", date.today()),
            discharge_date=data.get("discharge_date", date.today()),
            time_in_hospital=data.get("time_in_hospital", 1),
            payer_code=data.get("payer_code", "Unknown"),
            medical_specialty=data.get("medical_specialty", "Unknown"),
            num_lab_procedures=data.get("num_lab_procedures", 0),
            num_procedures=data.get("num_procedures", 0),
            num_medications=data.get("num_medications", 0),
            number_outpatient=data.get("number_outpatient", 0),
            number_emergency=data.get("number_emergency", 0),
            number_inpatient=data.get("number_inpatient", 0),
            number_diagnoses=data.get("number_diagnoses", 1),
        )
        db.add(enc)

        # Add outcome
        readmitted_raw = data.get("readmitted_raw", "NO")
        outcome = Outcome(
            encounter_id=enc.encounter_id,
            readmitted_raw=readmitted_raw,
            readmitted_30d=readmitted_raw == "<30",
            is_mortality=data.get("discharge_disposition_id") in [11, 19, 20, 21],
        )
        db.add(outcome)

        db.commit()
        db.refresh(enc)

        log_audit_event(
            db=db,
            username=username,
            action="CREATE",
            entity_name="encounter",
            entity_id=str(enc.encounter_id),
            details={"patient_nbr": enc.patient_nbr, "time_in_hospital": enc.time_in_hospital},
            user_id=user_id,
        )
        return enc

    @staticmethod
    def update_encounter(
        db: Session,
        encounter_id: int,
        update_data: Dict[str, Any],
        username: str = "system",
        user_id: Optional[int] = None,
    ) -> Optional[Encounter]:
        """Update existing encounter and record change diffs."""
        enc = db.query(Encounter).filter(Encounter.encounter_id == encounter_id).first()
        if not enc:
            return None

        diffs = {}
        fields = [
            "admission_type_id", "discharge_disposition_id", "admission_source_id",
            "time_in_hospital", "medical_specialty", "num_medications", "num_lab_procedures"
        ]

        for field in fields:
            if field in update_data and update_data[field] is not None:
                old_val = getattr(enc, field)
                new_val = update_data[field]
                if old_val != new_val:
                    diffs[field] = {"old": old_val, "new": new_val}
                    setattr(enc, field, new_val)

        if "readmitted_raw" in update_data and update_data["readmitted_raw"] is not None:
            if enc.outcome:
                old_readmit = enc.outcome.readmitted_raw
                new_readmit = update_data["readmitted_raw"]
                if old_readmit != new_readmit:
                    diffs["readmitted_raw"] = {"old": old_readmit, "new": new_readmit}
                    enc.outcome.readmitted_raw = new_readmit
                    enc.outcome.readmitted_30d = (new_readmit == "<30")

        if diffs:
            db.commit()
            db.refresh(enc)
            log_audit_event(
                db=db,
                username=username,
                action="UPDATE",
                entity_name="encounter",
                entity_id=str(encounter_id),
                details=diffs,
                user_id=user_id,
            )

        return enc

    @staticmethod
    def delete_encounter(
        db: Session,
        encounter_id: int,
        username: str = "system",
        user_id: Optional[int] = None,
    ) -> bool:
        """Delete encounter record and associated relations."""
        enc = db.query(Encounter).filter(Encounter.encounter_id == encounter_id).first()
        if not enc:
            return False

        db.delete(enc)
        db.commit()

        log_audit_event(
            db=db,
            username=username,
            action="DELETE",
            entity_name="encounter",
            entity_id=str(encounter_id),
            details={"deleted": True},
            user_id=user_id,
        )
        return True
