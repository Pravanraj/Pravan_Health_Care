"""Unit tests for Data Quality rules and validation engine."""

import pandas as pd
from datetime import date, timedelta
from src.etl.data_quality import evaluate_data_quality


def test_data_quality_detects_duplicates():
    """Verify that duplicate encounter records are flagged and removed."""
    df = pd.DataFrame({
        "encounter_id": [101, 101, 102],
        "patient_nbr": [1, 1, 2],
        "admission_type_id": [1, 1, 1],
        "discharge_disposition_id": [1, 1, 1],
        "admission_source_id": [7, 7, 7],
        "time_in_hospital": [3, 3, 2],
        "admission_date": [date(2000, 1, 1), date(2000, 1, 1), date(2000, 1, 5)],
        "discharge_date": [date(2000, 1, 4), date(2000, 1, 4), date(2000, 1, 7)],
    })

    valid_df, result = evaluate_data_quality(df, {1}, {1}, {7})

    assert result.duplicates_count == 1
    assert len(valid_df) == 2


def test_data_quality_detects_inconsistent_dates():
    """Verify detection when discharge precedes admission."""
    df = pd.DataFrame({
        "encounter_id": [201],
        "patient_nbr": [10],
        "admission_type_id": [1],
        "discharge_disposition_id": [1],
        "admission_source_id": [7],
        "time_in_hospital": [3],
        "admission_date": [date(2005, 5, 10)],
        "discharge_date": [date(2005, 5, 8)],  # Invalid: precedes admission
    })

    _, result = evaluate_data_quality(df, {1}, {1}, {7})
    assert result.inconsistent_dates_count == 1
    assert result.flagged_records == 1


def test_data_quality_detects_invalid_codes():
    """Verify that out-of-range reference codes are flagged."""
    df = pd.DataFrame({
        "encounter_id": [301],
        "patient_nbr": [12],
        "admission_type_id": [999],  # Invalid code
        "discharge_disposition_id": [1],
        "admission_source_id": [7],
        "time_in_hospital": [4],
        "admission_date": [date(2002, 3, 1)],
        "discharge_date": [date(2002, 3, 5)],
    })

    _, result = evaluate_data_quality(df, {1, 2}, {1}, {7})
    assert result.invalid_codes_count == 1
