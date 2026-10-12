"""Reporting service for exporting datasets and scheduled operational summaries."""

import io
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy.orm import Session

from src.database.models import Encounter, Patient, Outcome, Diagnosis
from src.services.analytics_service import AnalyticsService


class ReportService:
    """Handles tabular data extraction, Excel formatting, and scheduled reporting."""

    @staticmethod
    def generate_encounters_dataframe(db: Session, limit: int = 5000) -> pd.DataFrame:
        """Fetch joined encounter reporting view as a Pandas DataFrame."""
        rows = (
            db.query(
                Encounter.encounter_id,
                Encounter.patient_nbr,
                Patient.gender,
                Patient.race,
                Patient.age_bracket,
                Encounter.admission_date,
                Encounter.discharge_date,
                Encounter.time_in_hospital,
                Encounter.medical_specialty,
                Encounter.num_medications,
                Encounter.num_lab_procedures,
                Outcome.readmitted_raw,
                Outcome.readmitted_30d,
            )
            .join(Patient, Encounter.patient_nbr == Patient.patient_nbr)
            .join(Outcome, Encounter.encounter_id == Outcome.encounter_id)
            .limit(limit)
            .all()
        )

        data = [
            {
                "Encounter ID": r.encounter_id,
                "Patient ID": r.patient_nbr,
                "Gender": r.gender,
                "Race": r.race,
                "Age Bracket": r.age_bracket,
                "Admission Date": str(r.admission_date),
                "Discharge Date": str(r.discharge_date),
                "Length of Stay (Days)": r.time_in_hospital,
                "Medical Specialty": r.medical_specialty,
                "Medications Count": r.num_medications,
                "Lab Procedures Count": r.num_lab_procedures,
                "Readmission Status": r.readmitted_raw,
                "30-Day Readmission": "Yes" if r.readmitted_30d else "No",
            }
            for r in rows
        ]

        return pd.DataFrame(data)

    @staticmethod
    def export_to_csv(db: Session, limit: int = 5000) -> io.StringIO:
        """Export encounters to CSV stream."""
        df = ReportService.generate_encounters_dataframe(db, limit)
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        return stream

    @staticmethod
    def export_to_excel(db: Session, limit: int = 5000) -> io.BytesIO:
        """Export encounters to formatted Excel spreadsheet."""
        df = ReportService.generate_encounters_dataframe(db, limit)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Encounters")
        output.seek(0)
        return output

    @staticmethod
    def generate_executive_summary_report(db: Session) -> Dict[str, Any]:
        """Generate high-level operational summary suitable for scheduled dispatch."""
        kpis = AnalyticsService.get_summary_kpis(db)
        readmit_cat = AnalyticsService.get_readmission_by_category(db)
        los_cohort = AnalyticsService.get_los_by_cohort(db)

        return {
            "report_name": "Hospital Operational & Readmission Executive Summary",
            "kpis": kpis,
            "readmission_by_diagnosis": readmit_cat.get("by_diagnosis", [])[:5],
            "los_by_admission_type": los_cohort.get("by_admission_type", []),
        }
