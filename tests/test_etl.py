"""Unit tests for Data Cleaning and Transformation utilities."""

import os
import pandas as pd
from datetime import date
from src.etl.cleaner import clean_dataframe, map_icd9_to_category, parse_ids_mapping


def test_map_icd9_to_category():
    """Verify clinical grouping of ICD-9 diagnosis codes."""
    assert map_icd9_to_category("250.01") == "Diabetes"
    assert map_icd9_to_category("250") == "Diabetes"
    assert map_icd9_to_category("414") == "Circulatory"
    assert map_icd9_to_category("428") == "Circulatory"
    assert map_icd9_to_category("486") == "Respiratory"
    assert map_icd9_to_category("584") == "Genitourinary"
    assert map_icd9_to_category("V57") == "Supplementary/External"
    assert map_icd9_to_category("?") == "Unknown"
    assert map_icd9_to_category(None) == "Unknown"


def test_clean_dataframe_missing_values():
    """Verify that '?' missing indicators are standardized."""
    raw_data = {
        "encounter_id": [101, 102],
        "patient_nbr": [501, 502],
        "race": ["Caucasian", "?"],
        "gender": ["Female", "Unknown/Invalid"],
        "age": ["[40-50)", "?"],
        "time_in_hospital": [3, 5],
        "admission_type_id": [1, 2],
        "discharge_disposition_id": [1, 1],
        "admission_source_id": [7, 7],
    }
    df = pd.DataFrame(raw_data)
    cleaned = clean_dataframe(df)

    assert cleaned.loc[1, "race"] == "Unknown"
    assert cleaned.loc[1, "gender"] == "Unknown"
    assert "admission_date" in cleaned.columns
    assert "discharge_date" in cleaned.columns
    assert cleaned.loc[0, "discharge_date"] > cleaned.loc[0, "admission_date"]


def test_parse_ids_mapping():
    """Verify parsing of multi-section IDS_mapping.csv."""
    sample_mapping_content = """admission_type_id,description
1,Emergency
2,Urgent

discharge_disposition_id,description
1,Discharged to home
11,Expired

admission_source_id,description
7,Emergency Room
"""
    tmp_path = "/tmp/test_mapping.csv"
    with open(tmp_path, "w") as f:
        f.write(sample_mapping_content)

    try:
        adm_types, dis_disps, adm_srcs = parse_ids_mapping(tmp_path)
        assert adm_types[1] == "Emergency"
        assert dis_disps[11] == "Expired"
        assert adm_srcs[7] == "Emergency Room"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
