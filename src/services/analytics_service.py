"""Clinical Analytics Service executing aggregate reporting queries."""

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case

from src.database.models import (
    Encounter,
    Patient,
    Outcome,
    Diagnosis,
    AdmissionType,
    Medication,
)


class AnalyticsService:
    """Computes aggregated hospital metrics, trends, and clinical KPIs."""

    @staticmethod
    def get_summary_kpis(db: Session) -> Dict[str, Any]:
        """Calculate high-level healthcare operational KPI cards."""
        total_encounters = db.query(func.count(Encounter.encounter_id)).scalar() or 0
        total_patients = db.query(func.count(Patient.patient_nbr)).scalar() or 0

        avg_los = db.query(func.avg(Encounter.time_in_hospital)).scalar() or 0.0

        # Readmission counts
        readmit_30d_count = (
            db.query(func.count(Outcome.encounter_id))
            .filter(Outcome.readmitted_30d == True)
            .scalar()
            or 0
        )

        readmit_any_count = (
            db.query(func.count(Outcome.encounter_id))
            .filter(Outcome.readmitted_raw.in_(["<30", ">30"]))
            .scalar()
            or 0
        )

        mortality_count = (
            db.query(func.count(Outcome.encounter_id))
            .filter(Outcome.is_mortality == True)
            .scalar()
            or 0
        )

        rate_30d = round((readmit_30d_count / total_encounters * 100), 2) if total_encounters > 0 else 0.0
        rate_any = round((readmit_any_count / total_encounters * 100), 2) if total_encounters > 0 else 0.0
        mortality_rate = round((mortality_count / total_encounters * 100), 2) if total_encounters > 0 else 0.0

        return {
            "total_encounters": total_encounters,
            "total_patients": total_patients,
            "avg_length_of_stay": round(float(avg_los), 2),
            "readmission_rate_30d_pct": rate_30d,
            "readmission_rate_total_pct": rate_any,
            "mortality_rate_pct": mortality_rate,
            "readmitted_30d_count": readmit_30d_count,
            "mortality_count": mortality_count,
        }

    @staticmethod
    def get_admissions_trend(db: Session) -> List[Dict[str, Any]]:
        """Compute admission and readmission volume trends over time."""
        # Group by year-month of admission_date
        records = (
            db.query(
                func.strftime("%Y-%m", Encounter.admission_date).label("year_month"),
                func.count(Encounter.encounter_id).label("total_admissions"),
                func.sum(case((Outcome.readmitted_30d == True, 1), else_=0)).label("readmitted_30d"),
                func.avg(Encounter.time_in_hospital).label("avg_los"),
            )
            .join(Outcome, Encounter.encounter_id == Outcome.encounter_id)
            .group_by("year_month")
            .order_by("year_month")
            .all()
        )

        return [
            {
                "period": r.year_month,
                "admissions": int(r.total_admissions),
                "readmissions_30d": int(r.readmitted_30d or 0),
                "avg_los": round(float(r.avg_los or 0), 2),
            }
            for r in records
        ]

    @staticmethod
    def get_los_by_cohort(db: Session) -> Dict[str, Any]:
        """Analyze Length of Stay across age brackets, gender, and admission types."""
        # By age bracket
        by_age = (
            db.query(
                Patient.age_bracket,
                func.count(Encounter.encounter_id).label("encounters"),
                func.avg(Encounter.time_in_hospital).label("avg_los"),
            )
            .join(Encounter, Patient.patient_nbr == Encounter.patient_nbr)
            .group_by(Patient.age_bracket)
            .order_by(Patient.age_bracket)
            .all()
        )

        # By admission type
        by_admission = (
            db.query(
                AdmissionType.description.label("admission_type"),
                func.count(Encounter.encounter_id).label("encounters"),
                func.avg(Encounter.time_in_hospital).label("avg_los"),
            )
            .join(Encounter, AdmissionType.admission_type_id == Encounter.admission_type_id)
            .group_by(AdmissionType.description)
            .order_by(desc("encounters"))
            .all()
        )

        return {
            "by_age": [
                {"age_bracket": r.age_bracket, "encounters": int(r.encounters), "avg_los": round(float(r.avg_los), 2)}
                for r in by_age
            ],
            "by_admission_type": [
                {"admission_type": r.admission_type, "encounters": int(r.encounters), "avg_los": round(float(r.avg_los), 2)}
                for r in by_admission
            ],
        }

    @staticmethod
    def get_readmission_by_category(db: Session) -> Dict[str, Any]:
        """Compute readmission rates across admission types, diagnosis categories, and specialties."""
        # By Primary Diagnosis Category
        by_diag = (
            db.query(
                Diagnosis.category_name,
                func.count(Encounter.encounter_id).label("total"),
                func.sum(case((Outcome.readmitted_30d == True, 1), else_=0)).label("readmitted_30d"),
            )
            .join(Encounter, Diagnosis.encounter_id == Encounter.encounter_id)
            .join(Outcome, Encounter.encounter_id == Outcome.encounter_id)
            .filter(Diagnosis.diag_seq == 1)
            .group_by(Diagnosis.category_name)
            .order_by(desc("total"))
            .all()
        )

        # By Admission Type
        by_adm = (
            db.query(
                AdmissionType.description,
                func.count(Encounter.encounter_id).label("total"),
                func.sum(case((Outcome.readmitted_30d == True, 1), else_=0)).label("readmitted_30d"),
            )
            .join(Encounter, AdmissionType.admission_type_id == Encounter.admission_type_id)
            .join(Outcome, Encounter.encounter_id == Outcome.encounter_id)
            .group_by(AdmissionType.description)
            .order_by(desc("total"))
            .all()
        )

        return {
            "by_diagnosis": [
                {
                    "category": r.category_name,
                    "total": int(r.total),
                    "readmitted_30d": int(r.readmitted_30d or 0),
                    "readmission_rate_pct": round(((r.readmitted_30d or 0) / r.total * 100), 2) if r.total > 0 else 0.0,
                }
                for r in by_diag
            ],
            "by_admission_type": [
                {
                    "admission_type": r.description,
                    "total": int(r.total),
                    "readmitted_30d": int(r.readmitted_30d or 0),
                    "readmission_rate_pct": round(((r.readmitted_30d or 0) / r.total * 100), 2) if r.total > 0 else 0.0,
                }
                for r in by_adm
            ],
        }

    @staticmethod
    def get_medication_impact(db: Session) -> List[Dict[str, Any]]:
        """Assess the association between insulin regimen changes and readmission."""
        records = (
            db.query(
                Medication.dosage_change,
                func.count(Medication.encounter_id).label("total"),
                func.sum(case((Outcome.readmitted_30d == True, 1), else_=0)).label("readmitted_30d"),
            )
            .join(Outcome, Medication.encounter_id == Outcome.encounter_id)
            .filter(Medication.medication_name == "insulin")
            .group_by(Medication.dosage_change)
            .all()
        )

        return [
            {
                "insulin_status": r.dosage_change,
                "total_patients": int(r.total),
                "readmitted_30d": int(r.readmitted_30d or 0),
                "readmission_rate_pct": round(((r.readmitted_30d or 0) / r.total * 100), 2) if r.total > 0 else 0.0,
            }
            for r in records
        ]
