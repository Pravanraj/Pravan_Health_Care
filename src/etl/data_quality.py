"""Data Quality Validation Engine implementing healthcare data integrity rules."""

from typing import Dict, Any, List, Set, Tuple
import pandas as pd


class DataQualityResult:
    """Holds summary metrics and flagged row details from data quality evaluation."""

    def __init__(self):
        self.total_records: int = 0
        self.passed_records: int = 0
        self.flagged_records: int = 0
        self.duplicates_count: int = 0
        self.inconsistent_dates_count: int = 0
        self.invalid_codes_count: int = 0
        self.missing_identifiers_count: int = 0
        self.implausible_los_count: int = 0
        self.rule_violations: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to serializable dictionary."""
        cleanliness_pct = (
            round((self.passed_records / self.total_records) * 100, 2)
            if self.total_records > 0
            else 100.0
        )
        return {
            "total_records": self.total_records,
            "passed_records": self.passed_records,
            "flagged_records": self.flagged_records,
            "cleanliness_percentage": cleanliness_pct,
            "metrics": {
                "duplicate_encounters": self.duplicates_count,
                "inconsistent_dates": self.inconsistent_dates_count,
                "invalid_reference_codes": self.invalid_codes_count,
                "missing_identifiers": self.missing_identifiers_count,
                "implausible_los": self.implausible_los_count,
            },
            "sample_violations": self.rule_violations[:20],
        }


def evaluate_data_quality(
    df: pd.DataFrame,
    valid_admission_types: Set[int],
    valid_disposition_types: Set[int],
    valid_source_types: Set[int],
) -> Tuple[pd.DataFrame, DataQualityResult]:
    """Validate DataFrame against healthcare quality rules and return cleaned records + report."""
    result = DataQualityResult()
    result.total_records = len(df)

    if df.empty:
        return df, result

    # Check 1: Duplicate encounter_id
    duplicate_mask = df.duplicated(subset=["encounter_id"], keep="first")
    result.duplicates_count = int(duplicate_mask.sum())

    # Check 2: Missing or invalid identifiers
    id_mask = (df["encounter_id"] <= 0) | (df["patient_nbr"] <= 0)
    result.missing_identifiers_count = int(id_mask.sum())

    # Check 3: Implausible Length of Stay (time_in_hospital <= 0 or > 365)
    los_mask = (df["time_in_hospital"] <= 0) | (df["time_in_hospital"] > 365)
    result.implausible_los_count = int(los_mask.sum())

    # Check 4: Inconsistent dates (discharge_date < admission_date)
    if "admission_date" in df.columns and "discharge_date" in df.columns:
        date_mask = df["discharge_date"] < df["admission_date"]
    else:
        date_mask = pd.Series([False] * len(df), index=df.index)
    result.inconsistent_dates_count = int(date_mask.sum())

    # Check 5: Invalid codes
    invalid_codes_mask = (
        (~df["admission_type_id"].isin(valid_admission_types))
        | (~df["discharge_disposition_id"].isin(valid_disposition_types))
        | (~df["admission_source_id"].isin(valid_source_types))
    )
    result.invalid_codes_count = int(invalid_codes_mask.sum())

    # Aggregate violations
    any_violation_mask = (
        duplicate_mask
        | id_mask
        | los_mask
        | date_mask
        | invalid_codes_mask
    )

    result.flagged_records = int(any_violation_mask.sum())
    result.passed_records = result.total_records - result.flagged_records

    # Capture sample violations
    for idx, row in df[any_violation_mask].head(25).iterrows():
        reasons = []
        if duplicate_mask.loc[idx]:
            reasons.append("Duplicate encounter_id")
        if id_mask.loc[idx]:
            reasons.append("Missing/invalid encounter or patient ID")
        if los_mask.loc[idx]:
            reasons.append("Length of stay out of bounds")
        if date_mask.loc[idx]:
            reasons.append("Discharge date precedes admission date")
        if invalid_codes_mask.loc[idx]:
            reasons.append("Admission/Discharge code not found in lookup dictionary")

        result.rule_violations.append({
            "encounter_id": int(row.get("encounter_id", 0)),
            "patient_nbr": int(row.get("patient_nbr", 0)),
            "reasons": reasons,
        })

    # Return valid subset (or deduplicated cleaned records)
    valid_df = df[~duplicate_mask].copy()
    return valid_df, result
