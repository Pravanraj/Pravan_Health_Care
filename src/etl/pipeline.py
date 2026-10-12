"""Full ETL Pipeline orchestrator for Initial and Incremental Healthcare Ingestion."""

import os
import sys
import time
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session

# Fix Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database.models import (
    AdmissionType,
    DischargeDisposition,
    AdmissionSource,
    Patient,
    Encounter,
    Diagnosis,
    LabResult,
    Medication,
    Outcome,
    AuditLog,
    ETLBatch,
)
from src.etl.cleaner import (
    parse_ids_mapping,
    clean_dataframe,
    map_icd9_to_category,
    MORTALITY_DISPOSITION_IDS,
    MEDICATION_COLUMNS,
)
from src.etl.data_quality import evaluate_data_quality, DataQualityResult


class HealthcareETLPipeline:
    """Manages data ingestion, validation, and relational persistence."""

    def __init__(self, db: Session):
        self.db = db

    def load_reference_mappings(self, mapping_path: str) -> None:
        """Load admission and discharge reference codes from IDS_mapping.csv."""
        adm_types, dis_disps, adm_sources = parse_ids_mapping(mapping_path)

        # Populate AdmissionType
        for idx, desc in adm_types.items():
            existing = self.db.query(AdmissionType).filter_by(admission_type_id=idx).first()
            if not existing:
                self.db.add(AdmissionType(admission_type_id=idx, description=desc))
            else:
                existing.description = desc

        # Populate DischargeDisposition
        for idx, desc in dis_disps.items():
            existing = self.db.query(DischargeDisposition).filter_by(discharge_disposition_id=idx).first()
            if not existing:
                self.db.add(DischargeDisposition(discharge_disposition_id=idx, description=desc))
            else:
                existing.description = desc

        # Populate AdmissionSource
        for idx, desc in adm_sources.items():
            existing = self.db.query(AdmissionSource).filter_by(admission_source_id=idx).first()
            if not existing:
                self.db.add(AdmissionSource(admission_source_id=idx, description=desc))
            else:
                existing.description = desc

        self.db.commit()

    def run_pipeline(
        self,
        data_source: Any,
        mapping_path: Optional[str] = None,
        batch_type: str = "INITIAL",
        limit_records: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute complete ETL workflow from CSV file or DataFrame into relational DB."""
        start_time = time.time()
        batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        if mapping_path and os.path.exists(mapping_path):
            self.load_reference_mappings(mapping_path)

        # Get valid reference keys
        valid_adm = {row[0] for row in self.db.query(AdmissionType.admission_type_id).all()}
        valid_disp = {row[0] for row in self.db.query(DischargeDisposition.discharge_disposition_id).all()}
        valid_src = {row[0] for row in self.db.query(AdmissionSource.admission_source_id).all()}

        # Read source data
        if isinstance(data_source, str):
            source_name = os.path.basename(data_source)
            if limit_records:
                df = pd.read_csv(data_source, nrows=limit_records)
            else:
                df = pd.read_csv(data_source)
        elif isinstance(data_source, pd.DataFrame):
            source_name = "in_memory_dataframe"
            df = data_source.head(limit_records) if limit_records else data_source
        else:
            raise ValueError("data_source must be a file path or pandas DataFrame")

        total_input_count = len(df)

        # Step 1: Clean and standardize
        cleaned_df = clean_dataframe(df)

        # Step 2: Evaluate Data Quality
        valid_df, dq_result = evaluate_data_quality(cleaned_df, valid_adm, valid_disp, valid_src)

        # Step 3: Relational Ingestion
        ingested_encounters = 0

        # Existing patient IDs in DB
        existing_patient_ids = {row[0] for row in self.db.query(Patient.patient_nbr).all()}
        existing_encounter_ids = {row[0] for row in self.db.query(Encounter.encounter_id).all()}

        new_patients = []
        new_encounters = []
        new_diagnoses = []
        new_labs = []
        new_meds = []
        new_outcomes = []

        seen_in_batch_patients = set()
        records = valid_df.to_dict(orient="records")

        for row in records:
            enc_id = int(row["encounter_id"])
            pat_nbr = int(row["patient_nbr"])

            if enc_id in existing_encounter_ids:
                continue  # Skip existing encounters for idempotent loads

            # Handle Patient Master
            if pat_nbr not in existing_patient_ids and pat_nbr not in seen_in_batch_patients:
                seen_in_batch_patients.add(pat_nbr)
                new_patients.append(
                    Patient(
                        patient_nbr=pat_nbr,
                        race=str(row["race"]),
                        gender=str(row["gender"]),
                        age_bracket=str(row["age"]),
                    )
                )

            # Encounter Record
            adm_type = int(row["admission_type_id"]) if int(row["admission_type_id"]) in valid_adm else 1
            dis_disp = int(row["discharge_disposition_id"]) if int(row["discharge_disposition_id"]) in valid_disp else 1
            adm_src = int(row["admission_source_id"]) if int(row["admission_source_id"]) in valid_src else 1

            enc = Encounter(
                encounter_id=enc_id,
                patient_nbr=pat_nbr,
                admission_type_id=adm_type,
                discharge_disposition_id=dis_disp,
                admission_source_id=adm_src,
                admission_date=row["admission_date"],
                discharge_date=row["discharge_date"],
                time_in_hospital=int(row["time_in_hospital"]),
                payer_code=str(row.get("payer_code", "Unknown")),
                medical_specialty=str(row.get("medical_specialty", "Unknown")),
                num_lab_procedures=int(row.get("num_lab_procedures", 0)),
                num_procedures=int(row.get("num_procedures", 0)),
                num_medications=int(row.get("num_medications", 0)),
                number_outpatient=int(row.get("number_outpatient", 0)),
                number_emergency=int(row.get("number_emergency", 0)),
                number_inpatient=int(row.get("number_inpatient", 0)),
                number_diagnoses=int(row.get("number_diagnoses", 0)),
            )
            new_encounters.append(enc)

            # Diagnoses (1, 2, 3)
            for seq, col_name in [(1, "diag_1"), (2, "diag_2"), (3, "diag_3")]:
                raw_diag = str(row.get(col_name, "Unknown"))
                cat = map_icd9_to_category(raw_diag)
                new_diagnoses.append(
                    Diagnosis(
                        encounter_id=enc_id,
                        diag_seq=seq,
                        icd9_code=raw_diag,
                        category_name=cat,
                    )
                )

            # Lab Results
            new_labs.append(
                LabResult(
                    encounter_id=enc_id,
                    max_glu_serum=str(row.get("max_glu_serum", "None")),
                    a1c_result=str(row.get("A1Cresult", "None")),
                )
            )

            # Medications
            has_ch = str(row.get("change", "No")) in ("Ch", "Yes")
            is_dm = str(row.get("diabetesMed", "No")) in ("Yes", "Y")
            for med_name in MEDICATION_COLUMNS:
                status = str(row.get(med_name, "No"))
                if status != "No":
                    new_meds.append(
                        Medication(
                            encounter_id=enc_id,
                            medication_name=med_name,
                            dosage_change=status,
                            diabetes_med="Yes" if is_dm else "No",
                            med_changed="Yes" if has_ch else "No",
                        )
                    )

            # Outcomes
            readmit_raw = str(row.get("readmitted", "NO"))
            is_30d = readmit_raw == "<30"
            is_mort = dis_disp in MORTALITY_DISPOSITION_IDS
            new_outcomes.append(
                Outcome(
                    encounter_id=enc_id,
                    readmitted_raw=readmit_raw,
                    readmitted_30d=is_30d,
                    is_mortality=is_mort,
                )
            )

            ingested_encounters += 1

            if len(new_encounters) >= 10000:
                if new_patients:
                    self.db.bulk_save_objects(new_patients)
                    new_patients = []
                self.db.bulk_save_objects(new_encounters)
                self.db.bulk_save_objects(new_diagnoses)
                self.db.bulk_save_objects(new_labs)
                self.db.bulk_save_objects(new_meds)
                self.db.bulk_save_objects(new_outcomes)
                self.db.commit()
                new_encounters, new_diagnoses, new_labs, new_meds, new_outcomes = [], [], [], [], []

        # Flush remaining objects
        if new_patients:
            self.db.bulk_save_objects(new_patients)
        if new_encounters:
            self.db.bulk_save_objects(new_encounters)
        if new_diagnoses:
            self.db.bulk_save_objects(new_diagnoses)
        if new_labs:
            self.db.bulk_save_objects(new_labs)
        if new_meds:
            self.db.bulk_save_objects(new_meds)
        if new_outcomes:
            self.db.bulk_save_objects(new_outcomes)
        self.db.commit()

        elapsed = round(time.time() - start_time, 2)

        # Record ETL Batch metadata
        batch_log = ETLBatch(
            batch_id=batch_id,
            source_filename=source_name,
            batch_type=batch_type,
            records_processed=total_input_count,
            records_clean=ingested_encounters,
            records_flagged=dq_result.flagged_records,
            status="COMPLETED",
            execution_time_seconds=elapsed,
        )
        self.db.add(batch_log)

        # Add Audit Log
        audit = AuditLog(
            username="system_etl",
            action="ETL_INGESTION",
            entity_name="etl_batch",
            entity_id=batch_id,
            details_json=json.dumps({
                "source": source_name,
                "batch_type": batch_type,
                "ingested_encounters": ingested_encounters,
                "flagged": dq_result.flagged_records,
                "time_sec": elapsed,
            }),
        )
        self.db.add(audit)

        self.db.commit()

        return {
            "batch_id": batch_id,
            "status": "COMPLETED",
            "batch_type": batch_type,
            "source": source_name,
            "records_processed": total_input_count,
            "records_ingested": ingested_encounters,
            "execution_time_seconds": elapsed,
            "data_quality": dq_result.to_dict(),
        }
