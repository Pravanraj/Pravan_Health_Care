"""Data cleaning and transformation utilities for historical healthcare records."""

from datetime import date, timedelta
from typing import Dict, Tuple, List, Any
import numpy as np
import pandas as pd


# 24 Diabetes medication columns in UCI dataset
MEDICATION_COLUMNS = [
    "metformin", "repaglinide", "nateglinide", "chlorpropamide",
    "glimepiride", "acetohexamide", "glipizide", "glyburide",
    "tolbutamide", "pioglitazone", "rosiglitazone", "acarbose",
    "miglitol", "troglitazone", "tolazamide", "examide",
    "citoglipton", "insulin", "glyburide-metformin", "glipizide-metformin",
    "glimepiride-pioglitazone", "metformin-rosiglitazone", "metformin-pioglitazone"
]

MORTALITY_DISPOSITION_IDS = {11, 19, 20, 21}


def parse_ids_mapping(filepath: str) -> Tuple[Dict[int, str], Dict[int, str], Dict[int, str]]:
    """Parse the tripartite IDS_mapping.csv into distinct lookup dictionaries."""
    admission_types: Dict[int, str] = {}
    discharge_dispositions: Dict[int, str] = {}
    admission_sources: Dict[int, str] = {}

    current_section = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if "admission_type_id" in line:
                current_section = "admission_type"
                continue
            elif "discharge_disposition_id" in line:
                current_section = "discharge_disposition"
                continue
            elif "admission_source_id" in line:
                current_section = "admission_source"
                continue

            parts = line.split(",", 1)
            if len(parts) == 2 and parts[0].strip().isdigit():
                idx = int(parts[0].strip())
                desc = parts[1].strip().strip('"')
                if current_section == "admission_type":
                    admission_types[idx] = desc
                elif current_section == "discharge_disposition":
                    discharge_dispositions[idx] = desc
                elif current_section == "admission_source":
                    admission_sources[idx] = desc

    return admission_types, discharge_dispositions, admission_sources


def map_icd9_to_category(icd9_code: Any) -> str:
    """Map ICD-9 diagnosis codes to primary clinical diagnosis categories."""
    if not icd9_code or pd.isna(icd9_code) or str(icd9_code).strip() in {"?", "Unknown", "None", ""}:
        return "Unknown"

    code_str = str(icd9_code).strip()

    # Diabetes diagnosis
    if code_str.startswith("250"):
        return "Diabetes"

    # V or E codes
    if code_str.startswith(("V", "E")):
        return "Supplementary/External"

    # Numerical parsing
    try:
        num = float(code_str.split(".")[0])
        if (390 <= num <= 459) or num == 785:
            return "Circulatory"
        elif (460 <= num <= 519) or num == 786:
            return "Respiratory"
        elif (520 <= num <= 579) or num == 787:
            return "Digestive"
        elif (580 <= num <= 629) or num == 788:
            return "Genitourinary"
        elif (140 <= num <= 239):
            return "Neoplasms"
        elif (710 <= num <= 739):
            return "Musculoskeletal"
        elif (800 <= num <= 999):
            return "Injury"
        else:
            return "Other"
    except (ValueError, TypeError):
        return "Other"


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Perform primary data cleaning on raw healthcare encounter DataFrame."""
    cleaned = df.copy()

    # Replace '?' with standardized placeholders
    cleaned.replace("?", np.nan, inplace=True)

    # Standardize string fields
    categorical_defaults = {
        "race": "Unknown",
        "gender": "Unknown",
        "age": "[50-60)",
        "payer_code": "Unknown",
        "medical_specialty": "Unknown",
        "diag_1": "Unknown",
        "diag_2": "Unknown",
        "diag_3": "Unknown",
        "max_glu_serum": "None",
        "A1Cresult": "None",
        "change": "No",
        "diabetesMed": "No",
        "readmitted": "NO"
    }

    for col, default_val in categorical_defaults.items():
        if col in cleaned.columns:
            cleaned[col] = cleaned[col].fillna(default_val).astype(str).str.strip()

    # Clean gender anomalies
    if "gender" in cleaned.columns:
        cleaned["gender"] = cleaned["gender"].replace({"Unknown/Invalid": "Unknown"})

    # Ensure integer fields
    numeric_cols = [
        "encounter_id", "patient_nbr", "admission_type_id",
        "discharge_disposition_id", "admission_source_id", "time_in_hospital",
        "num_lab_procedures", "num_procedures", "num_medications",
        "number_outpatient", "number_emergency", "number_inpatient", "number_diagnoses"
    ]

    for col in numeric_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce").fillna(0).astype(int)

    # Clean medication columns
    for med in MEDICATION_COLUMNS:
        if med in cleaned.columns:
            cleaned[med] = cleaned[med].fillna("No").astype(str).str.strip()
        else:
            cleaned[med] = "No"

    # Synthesize consistent dates across 1999-2008 based on encounter sequence and LOS
    base_date = date(1999, 1, 1)
    if "admission_date" not in cleaned.columns:
        # Generate distributed chronological dates
        step_days = np.linspace(0, 3650, len(cleaned), dtype=int)
        admission_dates = [base_date + timedelta(days=int(d)) for d in step_days]
        cleaned["admission_date"] = admission_dates

    cleaned["discharge_date"] = [
        adm + timedelta(days=max(1, int(los)))
        for adm, los in zip(cleaned["admission_date"], cleaned["time_in_hospital"])
    ]

    return cleaned
